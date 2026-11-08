import calendar
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import unittest
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import configure_mappers

from app import create_app
from app.extensions import db
from app.models import User, RentPayment


class RentalManagementTest(unittest.TestCase):
    def setUp(self):
        database_url = os.environ.get('RENTAL_TEST_DATABASE_URL', 'sqlite:///:memory:')
        parsed = make_url(database_url)
        if parsed.get_backend_name() != 'sqlite' and not (parsed.database or '').startswith('codex_rental_test'):
            raise RuntimeError('Las pruebas solo permiten una base PostgreSQL descartable codex_rental_test*')
        self.app = create_app({'TESTING': True, 'AUTH_RATE_LIMIT_ENABLED': False, 'SQLALCHEMY_DATABASE_URI': database_url,
                               'JWT_SECRET_KEY': 'synthetic-test-key-not-for-production-12345'})
        self.context = self.app.app_context()
        self.context.push()
        if db.engine.dialect.name == 'sqlite':
            @event.listens_for(db.engine, 'connect')
            def enable_foreign_keys(connection, record):
                connection.execute('PRAGMA foreign_keys=ON')
        configure_mappers()
        db.create_all()
        user = User(username='test-admin', email='admin@example.invalid', role='admin')
        user.set_password('synthetic-admin-password')
        db.session.add(user)
        db.session.commit()
        self.client = self.app.test_client()
        response = self.client.post('/api/auth/login', json={'username': 'test-admin', 'password': 'synthetic-admin-password'})
        self.auth_header = 'Bearer ' + response.get_json()['access_token']
        self.client.environ_base['HTTP_AUTHORIZATION'] = self.auth_header
        self.today = date.today()
        self.year, self.month = self.today.year, self.today.month
        self.start = date(self.year, self.month, 1)
        self.end = date(self.year + 1, self.month, min(self.today.day, calendar.monthrange(self.year + 1, self.month)[1]))
        self.tenant = self.post('persons', {'first_name': 'Inquilino', 'last_name': 'Prueba', 'dni': 'TEST-T'})
        self.owner = self.post('persons', {'first_name': 'Propietario', 'last_name': 'Prueba', 'dni': 'TEST-O'})
        self.property = self.post('properties', {'title': 'Prueba', 'address': 'Prueba', 'price': '1000.00', 'operation_type': 'alquiler'})
        self.ownership = self.post('property-owners', {'property_id': self.property['id'], 'person_id': self.owner['id']})
        self.contract = self.post('contracts', {
            'property_id': self.property['id'], 'tenant_id': self.tenant['id'],
            'start_date': self.start.isoformat(), 'end_date': self.end.isoformat(),
            'initial_rent': '1000.00', 'current_rent': '1000.00', 'administration_percentage': '10.00',
            'adjustment_frequency_months': 3})
        self.charge = self.post('charges', {'contract_id': self.contract['id'], 'period_year': self.year,
            'period_month': self.month, 'due_date': self.today.isoformat()})

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def post(self, resource, body, status=201):
        response = self.client.post('/api/' + resource, json=body)
        self.assertEqual(response.status_code, status, response.get_json())
        return response.get_json()

    def get(self, path):
        response = self.client.get('/api/' + path)
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()

    def payment(self, amount='400.00', reference='PAY-1', **updates):
        data = {'contract_id': self.contract['id'], 'charge_id': self.charge['id'],
                'payment_date': self.today.isoformat(), 'amount': amount, 'payment_method': 'bank_transfer',
                'reference': reference, 'idempotency_key': reference}
        data.update(updates)
        return data

    def settlement(self, **updates):
        data = {'property_id': self.property['id'], 'owner_id': self.owner['id'], 'period_year': self.year,
                'period_month': self.month, 'settlement_date': self.today.isoformat(), 'idempotency_key': 'SET-1'}
        data.update(updates)
        return data

    def transfer(self, settlement, amount='100.00', reference='TR-1', **updates):
        data = {'settlement_id': settlement['id'], 'transfer_date': self.today.isoformat(), 'amount': amount,
                'payment_method': 'bank_transfer', 'reference': reference, 'idempotency_key': reference}
        data.update(updates)
        return data

    def test_partial_payments_and_tenant_debt(self):
        self.post('payments', self.payment())
        balance = self.get(f"charges/{self.charge['id']}/balance")
        self.assertEqual(balance['outstanding_balance'], '600.00')
        self.assertEqual(balance['status'], 'partial')
        debt = self.get(f"persons/{self.tenant['id']}/debts")
        self.assertEqual(debt['balances_by_currency'], {'ARS': '600.00'})
        self.post('payments', self.payment('600.00', 'PAY-2'))
        self.assertEqual(self.get(f"charges/{self.charge['id']}")['status'], 'paid')
        self.assertEqual(self.get(f"persons/{self.tenant['id']}/debts")['charges'], [])

    def test_overpayment_and_negative_amount_roll_back(self):
        self.post('payments', self.payment('1000.01'), 409)
        self.post('payments', self.payment('-1.00'), 400)
        self.post('payments', self.payment('0.00'), 409)
        self.assertEqual(self.get('payments'), [])
        self.assertEqual(self.get(f"charges/{self.charge['id']}/balance")['outstanding_balance'], '1000.00')

    def test_duplicate_payment_and_idempotency(self):
        data = self.payment()
        payment = self.post('payments', data)
        retried = self.post('payments', data)
        self.assertEqual(retried['id'], payment['id'])
        self.post('payments', self.payment('401.00'), 409)
        self.post('payments', self.payment(idempotency_key='different-key'), 409)
        self.assertEqual(len(self.get('payments')), 1)

    def test_contract_charge_mismatch_and_missing_fk(self):
        other = self.post('contracts', {'property_id': self.property['id'], 'tenant_id': self.tenant['id'],
            'start_date': self.start.isoformat(), 'end_date': self.end.isoformat(), 'initial_rent': '100', 'current_rent': '100', 'status': 'terminated'})
        self.post('payments', self.payment(contract_id=other['id']), 400)
        self.post('payments', self.payment(charge_id=999), 404)
        self.assertEqual(self.get('payments'), [])

    def test_payment_when_contract_and_charge_ids_differ(self):
        body = {'property_id': self.property['id'], 'tenant_id': self.tenant['id'],
                'start_date': self.start.isoformat(), 'end_date': self.end.isoformat(),
                'initial_rent': '100', 'current_rent': '100'}
        self.client.patch(f"/api/contracts/{self.contract['id']}", json={'status': 'terminated'})
        self.post('contracts', {**body, 'status': 'terminated'})
        contract = self.post('contracts', body)
        charge = self.post('charges', {'contract_id': contract['id'], 'period_year': self.year,
            'period_month': self.month, 'due_date': self.today.isoformat()})
        self.assertNotEqual(contract['id'], charge['id'])
        payment = self.post('payments', self.payment('50', contract_id=contract['id'], charge_id=charge['id']))
        self.assertEqual(payment['contract_id'], contract['id'])
        self.assertEqual(self.get(f"charges/{charge['id']}/balance")['outstanding_balance'], '50.00')

    def test_charge_duplicate_period(self):
        self.post('charges', {'contract_id': self.contract['id'], 'period_year': self.year,
            'period_month': self.month, 'due_date': self.today.isoformat()}, 409)
        self.assertEqual(len(self.get('charges')), 1)

    def test_historical_charge_is_not_repriced(self):
        response = self.client.put(f"/api/contracts/{self.contract['id']}", json={'current_rent': '2000.00', 'administration_percentage': '20'})
        self.assertEqual(response.status_code, 200, response.get_json())
        charge = self.get(f"charges/{self.charge['id']}")
        self.assertEqual(charge['rent_amount'], '1000.00')
        self.assertEqual(charge['administration_percentage'], '10.00')
        self.post('payments', self.payment('1000.00'))
        settlement = self.post('settlements', self.settlement())
        self.assertEqual(settlement['administration_fee'], '100.00')

    def test_settlement_requires_collected_funds(self):
        self.post('settlements', self.settlement(gross_amount='1'), 409)
        self.post('payments', self.payment())
        self.post('settlements', self.settlement(gross_amount='401'), 409)
        settlement = self.post('settlements', self.settlement())
        self.assertEqual(settlement['gross_amount'], '400.00')
        self.assertEqual(settlement['administration_fee'], '40.00')
        self.assertEqual(settlement['net_amount'], '360.00')
        self.post('settlements', self.settlement(idempotency_key='SET-2'), 409)
        self.assertEqual(self.post('settlements', self.settlement())['id'], settlement['id'])

    def test_partial_transfers_and_owner_balance(self):
        self.post('payments', self.payment())
        settlement = self.post('settlements', self.settlement())
        self.post('transfers', self.transfer(settlement, '100'))
        result = self.get(f"settlements/{settlement['id']}/balance")
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['outstanding_balance'], '260.00')
        balances = self.get(f"persons/{self.owner['id']}/settlements")
        self.assertEqual(balances['balances_by_currency'], {'ARS': '260.00'})
        self.post('transfers', self.transfer(settlement, '261', 'TR-OVER'), 409)
        self.post('transfers', self.transfer(settlement, '260', 'TR-2'))
        self.assertEqual(self.get(f"settlements/{settlement['id']}")['status'], 'transferred')

    def test_transfer_duplicates(self):
        self.post('payments', self.payment())
        settlement = self.post('settlements', self.settlement())
        data = self.transfer(settlement)
        transfer = self.post('transfers', data)
        self.assertEqual(self.post('transfers', data)['id'], transfer['id'])
        self.post('transfers', self.transfer(settlement, idempotency_key='TR-OTHER'), 409)
        self.assertEqual(len(self.get('transfers')), 1)

    def test_cancellation_dependency_order_and_audit(self):
        payment = self.post('payments', self.payment())
        settlement = self.post('settlements', self.settlement())
        transfer = self.post('transfers', self.transfer(settlement))
        self.post(f"payments/{payment['id']}/cancel", {'reason': 'Corrección'}, 409)
        self.post(f"settlements/{settlement['id']}/cancel", {'reason': 'Corrección'}, 409)
        self.post(f"transfers/{transfer['id']}/cancel", {'reason': 'Corrección'}, 200)
        self.post(f"settlements/{settlement['id']}/cancel", {'reason': 'Corrección'}, 200)
        cancelled = self.post(f"payments/{payment['id']}/cancel", {'reason': 'Corrección'}, 200)
        self.assertIsNotNone(cancelled['cancelled_at'])
        self.assertEqual(cancelled['cancellation_reason'], 'Corrección')
        self.assertEqual(len(self.get('payments')), 1)
        self.assertEqual(self.get(f"charges/{self.charge['id']}/balance")['outstanding_balance'], '1000.00')
        self.post('payments', self.payment(), 409)

    def test_cancel_charge_with_payment_is_rejected(self):
        self.post('payments', self.payment())
        self.post(f"charges/{self.charge['id']}/cancel", {'reason': 'Corrección'}, 409)
        self.post(f"charges/{self.charge['id']}/cancel", {}, 400)

    def test_ownership_limits_and_owner_available_share(self):
        response = self.client.put(f"/api/property-owners/{self.ownership['id']}", json={'ownership_percentage': '50'})
        self.assertEqual(response.status_code, 200, response.get_json())
        other = self.post('persons', {'first_name': 'Otro', 'last_name': 'Propietario'})
        self.post('property-owners', {'property_id': self.property['id'], 'person_id': other['id'], 'ownership_percentage': '51'}, 400)
        self.post('property-owners', {'property_id': self.property['id'], 'person_id': other['id'], 'ownership_percentage': '50'})
        self.post('payments', self.payment('1000'))
        self.post('settlements', self.settlement(gross_amount='501'), 409)
        first = self.post('settlements', self.settlement())
        second = self.post('settlements', self.settlement(owner_id=other['id'], idempotency_key='SET-2'))
        self.assertEqual(first['gross_amount'], '500.00')
        self.assertEqual(second['gross_amount'], '500.00')

    def test_financial_validation(self):
        for amount in ('NaN', 'Infinity', '1.001', True, '10000000000'):
            with self.subTest(amount=amount):
                self.post('payments', self.payment(amount), 400)
        self.post('payments', self.payment(payment_date='2026-02-30'), 400)
        self.post('payments', self.payment(payment_date=(self.today + timedelta(days=1)).isoformat()), 400)
        self.post('payments', self.payment(idempotency_key=None), 400)
        self.post('payments', self.payment(reference=None), 400)
        self.assertEqual(self.get('payments'), [])

    def test_discount_and_period_validation(self):
        self.post('charges', {'contract_id': self.contract['id'], 'period_year': self.year,
            'period_month': 13, 'due_date': self.today.isoformat()}, 400)
        self.post('charges', {'contract_id': self.contract['id'], 'period_year': self.year,
            'period_month': self.month, 'due_date': self.today.isoformat(), 'discounts': '1001'}, 400)
        self.assertEqual(len(self.get('charges')), 1)

    def test_contract_dates_and_percentage(self):
        base = {'property_id': self.property['id'], 'tenant_id': self.tenant['id'], 'start_date': self.start.isoformat(),
                'end_date': self.start.isoformat(), 'initial_rent': '1', 'current_rent': '1'}
        self.post('contracts', base, 400)
        self.post('contracts', {**base, 'end_date': self.end.isoformat(), 'administration_percentage': '101'}, 400)
        self.post('contracts', {**base, 'end_date': self.end.isoformat(), 'adjustment_frequency_months': 0}, 400)

    def test_settlement_deductions_and_transfer_dates(self):
        self.post('payments', self.payment())
        self.post('settlements', self.settlement(administration_fee='401'), 400)
        self.post('settlements', self.settlement(deductions='361'), 400)
        settlement = self.post('settlements', self.settlement())
        self.post('transfers', self.transfer(settlement, transfer_date=(self.today - timedelta(days=1)).isoformat()), 400)
        self.post('transfers', self.transfer(settlement, '-1'), 400)

    def test_dashboard(self):
        self.post('payments', self.payment())
        settlement = self.post('settlements', self.settlement())
        self.post('expenses', {'property_id': self.property['id'], 'expense_date': self.today.isoformat(),
            'category': 'repair', 'description': 'Prueba', 'amount': '25.50', 'responsible_party': 'agency'})
        totals = self.get(f'dashboard?year={self.year}&month={self.month}')
        self.assertEqual(totals['collections'], '400.00')
        self.assertEqual(totals['pending'], '600.00')
        self.assertEqual(totals['administration_fees'], '40.00')
        self.assertEqual(totals['expenses'], '25.50')
        self.assertEqual(totals['pending_owner_transfers'], '360.00')
        empty = self.get(f'dashboard?year={self.year}&month={self.month}&currency=USD')
        self.assertEqual(empty['collections'], '0.00')
        self.assertEqual(self.client.get('/api/dashboard?year=bad&month=1').status_code, 400)

    def test_existing_property_endpoints_and_crud(self):
        self.assertEqual(len(self.get('properties')), 1)
        self.assertEqual(self.get(f"properties/{self.property['id']}")['title'], 'Prueba')
        response = self.client.put(f"/api/properties/{self.property['id']}", json={'title': 'Actualizada'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['title'], 'Actualizada')
        self.assertEqual(self.client.delete(f"/api/properties/{self.property['id']}").status_code, 409)
        self.assertEqual(self.client.put(f"/api/properties/{self.property['id']}", json={'price': '-1'}).status_code, 400)
        reminder = self.post('reminders', {'contract_id': self.contract['id'], 'title': 'Prueba', 'due_date': self.today.isoformat()})
        response = self.client.patch(f"/api/reminders/{reminder['id']}", json={'status': 'completed'})
        self.assertIsNotNone(response.get_json()['completed_at'])
        self.assertEqual(self.client.delete(f"/api/reminders/{reminder['id']}").status_code, 200)
        document = self.post('documents', {'person_id': self.tenant['id'], 'document_type': 'contract',
            'file_path': 'https://example.invalid/contract.pdf', 'original_filename': 'contract.pdf'})
        self.assertIsNotNone(document['uploaded_at'])
        self.assertEqual(self.client.delete(f"/api/documents/{document['id']}").status_code, 200)

    def test_upcoming_contracts_and_adjustments(self):
        response = self.client.put(f"/api/contracts/{self.contract['id']}", json={'adjustment_frequency_months': 1})
        self.assertEqual(response.status_code, 200)
        next_month = self.start.replace(year=self.year + (self.month == 12), month=self.month % 12 + 1)
        adjustment = self.post('adjustments', {'contract_id': self.contract['id'], 'effective_date': next_month.isoformat(),
            'previous_amount': '1000', 'new_amount': '1100', 'adjustment_percentage': '10.0000'})
        upcoming = self.get('contracts/upcoming-adjustments?days=45')
        self.assertEqual(upcoming[0]['next_adjustment_date'], next_month.isoformat())
        expiring = self.get('contracts/upcoming-expirations?days=400')
        self.assertEqual(expiring[0]['id'], self.contract['id'])
        self.assertEqual(self.client.get('/api/contracts/upcoming-adjustments?days=-1').status_code, 400)
        self.assertEqual(self.client.delete(f"/api/adjustments/{adjustment['id']}").status_code, 200)

    def test_financial_records_have_no_delete_or_update_endpoint(self):
        payment = self.post('payments', self.payment())
        self.assertEqual(self.client.delete(f"/api/payments/{payment['id']}").status_code, 405)
        self.assertEqual(self.client.put(f"/api/payments/{payment['id']}", json={'amount': '1'}).status_code, 405)

    def test_user_password_is_hashed(self):
        user = User(username='test', email='test@example.invalid')
        user.set_password('synthetic-test-password')
        self.assertNotEqual(user.password_hash, 'synthetic-test-password')
        self.assertTrue(user.check_password('synthetic-test-password'))
        self.assertFalse(user.check_password('wrong'))
        db.session.add(user)
        db.session.commit()

    def test_database_rejects_invalid_direct_payment(self):
        payment = RentPayment(contract_id=self.contract['id'], charge_id=self.charge['id'], payment_date=self.today,
            amount=Decimal('-1'), payment_method='cash', reference='invalid', idempotency_key='invalid')
        db.session.add(payment)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        self.assertEqual(self.get('payments'), [])

    def test_backdated_settlement_cannot_use_later_receipts(self):
        if self.today == self.start:
            self.skipTest('El primer día del mes no hay fecha anterior dentro del contrato')
        self.post('payments', self.payment())
        self.post('settlements', self.settlement(settlement_date=(self.today - timedelta(days=1)).isoformat()), 409)

    def test_database_rejects_cross_contract_payment(self):
        other = self.post('contracts', {'property_id': self.property['id'], 'tenant_id': self.tenant['id'],
            'start_date': self.start.isoformat(), 'end_date': self.end.isoformat(), 'initial_rent': '100', 'current_rent': '100', 'status': 'terminated'})
        db.session.add(RentPayment(contract_id=other['id'], charge_id=self.charge['id'], payment_date=self.today,
            amount=Decimal('1'), payment_method='cash', reference='invalid', idempotency_key='invalid'))
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def concurrent_posts(self, resource, first, second):
        if db.engine.dialect.name != 'postgresql':
            self.skipTest('Bloqueos concurrentes requieren PostgreSQL')
        barrier = Barrier(2)
        def worker(body):
            with self.app.test_client() as client:
                barrier.wait(timeout=10)
                response = client.post('/api/' + resource, json=body, headers={'Authorization': self.auth_header})
                return response.status_code, response.get_json()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker, body) for body in (first, second)]
            results = [future.result(timeout=20) for future in futures]
        self.assertEqual(sorted(status for status, body in results), [201, 409], results)
        db.session.expire_all()

    def test_concurrent_payments_cannot_overpay(self):
        self.concurrent_posts('payments', self.payment('600', 'CONCURRENT-1'), self.payment('600', 'CONCURRENT-2'))
        self.assertEqual(self.get(f"charges/{self.charge['id']}/balance")['outstanding_balance'], '400.00')

    def test_concurrent_settlements_cannot_overallocate(self):
        self.post('payments', self.payment('1000'))
        self.concurrent_posts('settlements', self.settlement(gross_amount='600'), self.settlement(gross_amount='600', idempotency_key='SET-2'))
        self.assertEqual(len(self.get('settlements')), 1)

    def test_concurrent_transfers_cannot_exceed_net(self):
        self.post('payments', self.payment('1000'))
        settlement = self.post('settlements', self.settlement())
        self.concurrent_posts('transfers', self.transfer(settlement, '500', 'CONCURRENT-1'), self.transfer(settlement, '500', 'CONCURRENT-2'))
        self.assertEqual(self.get(f"settlements/{settlement['id']}/balance")['outstanding_balance'], '400.00')

    def test_bad_json_and_unknown_fields(self):
        response = self.client.post('/api/payments', data='{', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        response = self.client.post('/api/payments', json=[])
        self.assertEqual(response.status_code, 400)
        self.post('payments', {**self.payment(), 'status': 'paid'}, 400)
        self.assertEqual(self.client.get('/api/payments?password=invalid').status_code, 400)


if __name__ == '__main__':
    unittest.main()
