import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
import test_rental_management as rental
from app.extensions import db
from app.models import AdjustmentQuote, OfficialIndex
from app.models.common import utcnow
from app.services.report_service import add_months
from app.services.official_index_service import IPC_SERIES


class OfficialIndicesAndFeesTest(unittest.TestCase):
    setUp = rental.RentalManagementTest.setUp
    tearDown = rental.RentalManagementTest.tearDown
    post = rental.RentalManagementTest.post
    get = rental.RentalManagementTest.get

    def preview_body(self, kind='IPC'):
        effective = add_months(self.start, 1)
        return {'kind': kind, 'start': self.start.isoformat(),
                'end': (self.start if kind == 'IPC' else effective).isoformat(), 'effective_date': effective.isoformat()}

    def ipc_payload(self, complete=True):
        return {'meta': [{}, {'field': {'id': IPC_SERIES}}], 'data': [
            [add_months(self.start, -1).isoformat(), 100], *([[self.start.isoformat(), 110]] if complete else [])]}

    def test_official_ipc_preview_apply_and_duplicate(self):
        body = self.preview_body()
        url = f"contracts/{self.contract['id']}/adjustment-preview"
        with patch('app.services.official_index_service.read_json', return_value=self.ipc_payload()) as download:
            quote = self.post(url, body, 200)
            again = self.post(url, body, 200)
            self.assertEqual(download.call_count, 1)  # Valid complete local snapshot reused.
        self.assertEqual(quote['new_amount'], '1100.00')
        self.assertEqual(self.get(f"contracts/{self.contract['id']}")['current_rent'], '1000.00')
        apply = {'mode': 'official', 'effective_date': body['effective_date'], 'quote_id': quote['quote_id'], 'new_amount': '1'}
        result = self.post(f"contracts/{self.contract['id']}/apply-adjustment", apply, 200)
        self.assertEqual(result['new_amount'], '1100.00')
        self.assertEqual(result['index_name'], 'IPC')
        self.assertIn(IPC_SERIES, result['source_url'])
        self.assertIn('observations', result['calculation_detail'])
        self.post(f"contracts/{self.contract['id']}/apply-adjustment", apply, 409)
        self.assertEqual(self.get(f"charges/{self.charge['id']}")['total_amount'], '1000.00')

    def test_missing_month_and_wrong_series_never_create_quote(self):
        url = f"contracts/{self.contract['id']}/adjustment-preview"
        with patch('app.services.official_index_service.read_json', return_value=self.ipc_payload(False)):
            self.post(url, self.preview_body(), 409)
        payload = self.ipc_payload()
        payload['meta'][1]['field']['id'] = 'wrong-series'
        with patch('app.services.official_index_service.read_json', return_value=payload):
            self.post(url, self.preview_body(), 503)
        self.assertEqual(db.session.query(AdjustmentQuote).count(), 0)
        self.assertEqual(db.session.query(OfficialIndex).count(), 0)

    def test_icl_exact_dates_expired_quote_and_source_failure(self):
        body = self.preview_body('ICL')
        payload = {'status': 200, 'results': [{'idVariable': 40, 'detalle': [
            {'fecha': body['start'], 'valor': '10.00000'}, {'fecha': body['end'], 'valor': '12.00000'}]}]}
        with patch('app.services.official_index_service.read_json', return_value=payload):
            quote = self.post(f"contracts/{self.contract['id']}/adjustment-preview", body, 200)
        self.assertEqual(quote['new_amount'], '1200.00')
        row = db.session.get(AdjustmentQuote, quote['quote_id'])
        row.expires_at = utcnow() - timedelta(seconds=1)
        db.session.commit()
        self.post(f"contracts/{self.contract['id']}/apply-adjustment", {'mode': 'official', 'quote_id': row.id, 'effective_date': body['effective_date']}, 409)
        with patch('app.services.official_index_service.urlopen', side_effect=TimeoutError):
            self.post(f"contracts/{self.contract['id']}/adjustment-preview", self.preview_body(), 503)

    def test_commission_partial_duplicate_reporting_and_cancellation(self):
        url = f"contracts/{self.contract['id']}/fees"
        body = {'amount': '200.00', 'currency': 'USD', 'payer': 'tenant', 'agreed_date': self.today.isoformat()}
        fee = self.post(url, body)
        self.post(url, body, 409)
        self.assertEqual(self.get(f"reports/business?year={self.year}&currency=USD")['months'][self.month-1]['closing_fees'], '0.00')
        payment = {'amount': '50', 'payment_date': self.today.isoformat(), 'method': 'transfer', 'reference': 'TEST', 'idempotency_key': 'fee-payment-1'}
        first = self.post(f"contract-fees/{fee['id']}/payments", payment, 200)
        retry = self.post(f"contract-fees/{fee['id']}/payments", payment, 200)
        self.assertEqual(len(retry['payments']), 1)
        self.assertEqual(retry['pending_amount'], '150.00')
        self.post(f"contract-fees/{fee['id']}/payments", {**payment, 'amount': '151', 'idempotency_key': 'fee-overpay'}, 409)
        report = self.get(f"reports/business?year={self.year}&currency=USD")['months'][self.month-1]
        self.assertEqual(report['closing_fees'], '50.00')
        self.assertEqual(report['result'], '50.00')
        self.assertEqual(self.get(f"charges/{self.charge['id']}")['outstanding_balance'], '1000.00')
        self.post(f"contract-fees/{fee['id']}/cancel", {'reason': 'Error'}, 409)
        self.post(f"contract-fee-payments/{first['payments'][0]['id']}/cancel", {'reason': 'Error de registro'}, 200)
        self.post(f"contract-fees/{fee['id']}/cancel", {'reason': 'Acuerdo corregido'}, 200)
        report = self.get(f"reports/business?year={self.year}&currency=USD")['months'][self.month-1]
        self.assertEqual(report['closing_fees'], '0.00')
        self.assertEqual(self.get(url)[0]['pending_amount'], '0.00')

    def test_commission_racing_payments_cannot_overcollect(self):
        if db.engine.dialect.name != 'postgresql':
            self.skipTest('El bloqueo concurrente se comprueba con PostgreSQL descartable')
        fee = self.post(f"contracts/{self.contract['id']}/fees", {'amount': '150', 'currency': 'ARS', 'payer': 'owner', 'agreed_date': self.today.isoformat()})
        barrier = Barrier(2)
        def attempt(index):
            with self.app.test_client() as client:
                barrier.wait(timeout=10)
                return client.post(f"/api/contract-fees/{fee['id']}/payments", headers={'Authorization': self.auth_header}, json={
                    'amount': '100', 'payment_date': self.today.isoformat(), 'method': 'cash', 'idempotency_key': f'race-fee-{index}'}).status_code
        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(attempt, [1, 2]))
        self.assertEqual(sorted(statuses), [200, 409])
        self.assertEqual(self.get(f"contracts/{self.contract['id']}/fees")[0]['paid_amount'], '100.00')

    def test_new_endpoints_require_administrator(self):
        from app.models import User
        operator = User(username='fee-operator', email='fee-operator@example.invalid', role='operator')
        operator.set_password('synthetic-operator-password')
        db.session.add(operator); db.session.commit()
        token = self.client.post('/api/auth/login', json={'username': operator.username, 'password': 'synthetic-operator-password'}).json['access_token']
        for path in [f"/api/contracts/{self.contract['id']}/fees", f"/api/contracts/{self.contract['id']}/adjustment-preview"]:
            response = self.client.post(path, json={}, headers={'Authorization': 'Bearer ' + token})
            self.assertEqual(response.status_code, 403)


if __name__ == '__main__':
    unittest.main()
