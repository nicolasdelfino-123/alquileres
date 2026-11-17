import unittest
import os
from decimal import Decimal
from unittest.mock import patch
import test_rental_workspace as workspace


class RealBillingPeriodsTest(unittest.TestCase):
    def setUp(self):
        from sqlalchemy.engine import make_url
        url = os.environ.get('RENTAL_TEST_DATABASE_URL', 'sqlite:///:memory:')
        parsed = make_url(url)
        if parsed.get_backend_name() != 'sqlite' and not (parsed.database or '').startswith('codex_rental_test'):
            raise RuntimeError('Solo se permite una base PostgreSQL descartable codex_rental_test*')
        factory = workspace.create_app
        with patch.object(workspace, 'create_app', side_effect=lambda config: factory({**config, 'SQLALCHEMY_DATABASE_URI': url})):
            workspace.RentalWorkspaceTest.setUp(self)
    tearDown = workspace.RentalWorkspaceTest.tearDown
    post = workspace.RentalWorkspaceTest.post

    def change_contract(self, **values):
        response = self.client.patch(f"/api/contracts/{self.contract['id']}", json=values)
        self.assertEqual(response.status_code, 200, response.json)
        self.contract = response.json

    def adjust(self, effective='2026-04-15', treatment=None, status=200):
        data = {'effective_date': effective, 'mode': 'percentage', 'percentage': '20'}
        if treatment:
            data['billing_treatment'] = treatment
        return self.post(f"/contracts/{self.contract['id']}/apply-adjustment", data, status)

    def charge(self, year=2026, month=4, due='2026-04-20'):
        return self.post('/charges', {'contract_id': self.contract['id'], 'period_year': year,
                                      'period_month': month, 'due_date': due})

    def test_midmonth_preview_confirmation_and_generated_charge_match(self):
        body = {'effective_date': '2026-04-15', 'mode': 'percentage', 'percentage': '20', 'billing_treatment': 'prorate'}
        preview = self.post(f"/contracts/{self.contract['id']}/manual-adjustment-preview", body, 200)
        self.assertEqual(preview['billing']['amount'], '1106666.67')
        self.assertEqual([row['days'] for row in preview['billing']['segments']], [14, 16])
        self.assertEqual(self.client.get(f"/api/contracts/{self.contract['id']}").json['current_rent'], '1000000.00')
        self.post(f"/contracts/{self.contract['id']}/apply-adjustment", {'mode': 'preview', 'quote_id': preview['quote_id'], 'effective_date': body['effective_date']}, 200)
        charge = self.charge()
        self.assertEqual(charge['rent_amount'], preview['billing']['amount'])
        self.assertEqual(charge['billing_start'], '2026-04-01')
        self.assertEqual(charge['billing_end'], '2026-04-30')
        self.assertEqual(sum(Decimal(row['amount']) for row in charge['rent_calculation']['segments']), Decimal(charge['rent_amount']))
        workspace_rows = self.client.get('/api/workspace?year=2026&month=4&currency=ARS').json
        self.assertEqual(workspace_rows['rows'][0]['rent_amount'], charge['rent_amount'])

    def test_midmonth_requires_explicit_agreement_and_blocks_existing_charge(self):
        self.adjust(status=400)
        charge = self.charge()
        self.adjust(treatment='prorate', status=409)
        unchanged = self.client.get(f"/api/charges/{charge['id']}").json
        self.assertEqual(unchanged['rent_amount'], '1000000.00')
        self.assertEqual(self.client.get(f"/api/contracts/{self.contract['id']}/adjustments").json, [])

    def test_next_period_does_not_reprice_existing_current_period(self):
        old = self.charge()
        self.adjust(treatment='next_period')
        may = self.charge(month=5, due='2026-05-10')
        self.assertEqual(may['rent_amount'], '1200000.00')
        self.assertEqual(self.client.get(f"/api/charges/{old['id']}").json['rent_amount'], '1000000.00')

    def test_whole_period_and_saved_default(self):
        self.change_contract(adjustment_billing_treatment='whole_period')
        self.adjust()
        self.assertEqual(self.charge()['rent_amount'], '1200000.00')

    def test_anniversary_fifteenth_to_fourteenth_and_locked_cycle(self):
        self.change_contract(start_date='2026-01-15', end_date='2027-01-14', billing_cycle='anniversary')
        self.adjust(effective='2026-04-15')
        charge = self.charge(due='2026-04-15')
        self.assertEqual((charge['billing_start'], charge['billing_end'], charge['rent_amount']), ('2026-04-15', '2026-05-14', '1200000.00'))
        self.assertEqual(self.client.patch(f"/api/contracts/{self.contract['id']}", json={'billing_cycle': 'calendar'}).status_code, 409)
        result = self.post('/charges/generate', {'year': 2027, 'month': 1, 'currency': 'ARS'}, 200)
        self.assertEqual(result['created'], [])

    def test_end_of_month_anchor_recovers_after_short_month(self):
        self.change_contract(start_date='2026-01-31', end_date='2027-01-30', billing_cycle='anniversary')
        feb = self.charge(month=2, due='2026-02-28')
        self.assertEqual((feb['billing_start'], feb['billing_end'], feb['rent_amount']), ('2026-02-28', '2026-03-30', '1000000.00'))
        self.adjust(effective='2026-04-30')
        contract = self.client.get(f"/api/contracts/{self.contract['id']}").json
        self.assertEqual(contract['next_adjustment_date'], '2026-07-31')
        settings = self.client.get(f"/api/contracts/{self.contract['id']}/adjustment-settings?effective_date=2026-07-31").json
        self.assertEqual(settings['initial_date'], '2026-04-30')

    def test_calendar_leap_february_and_initial_partial_period(self):
        self.change_contract(start_date='2024-02-15')
        charge = self.charge(year=2024, month=2, due='2024-02-20')
        self.assertEqual(charge['rent_calculation']['period_days'], 29)
        self.assertEqual(charge['rent_calculation']['segments'][0]['days'], 15)
        self.assertEqual(charge['rent_amount'], '517241.38')

    def test_official_icl_accepts_real_midmonth_dates(self):
        payload = {'status': 200, 'results': [{'idVariable': 40, 'detalle': [
            {'fecha': '2026-01-01', 'valor': '10'}, {'fecha': '2026-04-15', 'valor': '12'}]}]}
        with patch('app.services.official_index_service.read_json', return_value=payload):
            quote = self.post(f"/contracts/{self.contract['id']}/adjustment-preview", {
                'kind': 'ICL', 'start': '2026-01-01', 'end': '2026-04-15',
                'effective_date': '2026-04-15', 'billing_treatment': 'prorate'}, 200)
        self.assertEqual(quote['new_amount'], '1200000.00')
        self.assertEqual(quote['billing']['amount'], '1106666.67')


if __name__ == '__main__':
    unittest.main()
