import unittest
from app import create_app
from app.extensions import db
from app.models import Reminder, RentCharge, RentPayment
from app.services.management_service import ManagementService, APIError
from app.services.utility_service import generate_controls, validate_rules

class UtilityRulesTest(unittest.TestCase):
    def setUp(self):
        self.app=create_app({'TESTING':True,'MAIL_WORKER_AUTOSTART':False,'SQLALCHEMY_DATABASE_URI':'sqlite:///:memory:'})
        self.context=self.app.app_context();self.context.push();db.create_all()
        self.person=ManagementService.create('persons',{'first_name':'Persona','last_name':'Prueba'})
        self.rule={'service':'municipal','payer':'tenant','management':'collect_pay','frequency':'monthly','day':31,'reference':'MUNI-TEST','notes':'Confirmar factura'}
        self.prop=ManagementService.create('properties',{'address':'Dirección de prueba','utility_rules':[self.rule]})
        self.contract=ManagementService.create('contracts',{'property_id':self.prop.id,'tenant_id':self.person.id,'start_date':'2026-01-01','end_date':'2027-12-31','initial_rent':'100','current_rent':'100','utility_rules':[self.rule]})
    def tearDown(self):
        db.session.remove();db.drop_all();self.context.pop()
    def test_monthly_controls_are_idempotent_and_not_debts(self):
        self.assertEqual(generate_controls(self.contract.id,{'year':2026,'month':2}),{'created':1,'existing':0})
        self.assertEqual(generate_controls(self.contract.id,{'year':2026,'month':2}),{'created':0,'existing':1})
        reminder=db.session.query(Reminder).one()
        self.assertEqual(reminder.due_date.isoformat(),'2026-02-28')
        self.assertIsNone(reminder.amount)
        self.assertEqual(reminder.responsible_person_id,self.person.id)
        self.assertEqual(db.session.query(RentCharge).count(),0)
        self.assertEqual(db.session.query(RentPayment).count(),0)
        reminder.status='completed';db.session.commit()
        self.assertEqual(generate_controls(self.contract.id,{'year':2026,'month':2})['created'],0)
        self.assertEqual(generate_controls(self.contract.id,{'year':2026,'month':3})['created'],1)
    def test_property_changes_do_not_change_contract_agreement(self):
        ManagementService.update('properties',self.prop.id,{'utility_rules':[]})
        self.assertEqual(self.contract.utility_rules[0]['payer'],'tenant')
    def test_invalid_and_ambiguous_inputs_are_rejected(self):
        for rules in [[self.rule,self.rule],[{**self.rule,'payer':'owner'}],[{**self.rule,'day':32}],[{**self.rule,'amount':'100'}]]:
            with self.assertRaises(APIError):validate_rules(rules)
        with self.assertRaises(APIError):generate_controls(self.contract.id,{'year':2028,'month':1})
    def test_custom_services_keep_reference_amount_without_creating_debt(self):
        custom={**self.rule,'service':'custom:'+'a'*32,'name':'Personal Flow','reference_amount':'25000.50'}
        saved=ManagementService.update('contracts',self.contract.id,{'utility_rules':[custom]})
        self.assertEqual(saved.utility_rules[0]['name'],'Personal Flow')
        self.assertEqual(generate_controls(self.contract.id,{'year':2026,'month':4})['created'],1)
        reminder=db.session.query(Reminder).one()
        self.assertIn('Personal Flow',reminder.title)
        self.assertIsNone(reminder.amount)
        self.assertEqual(db.session.query(RentCharge).count(),0)
        with self.assertRaises(APIError):validate_rules([{**custom,'name':''}])
        with self.assertRaises(APIError):validate_rules([{**custom,'reference_amount':'-1'}])

    def test_recorded_debt_can_have_unknown_amount(self):
        reminder=ManagementService.create('reminders',{'property_id':self.prop.id,'contract_id':self.contract.id,'title':'Deuda municipal informada','category':'Deuda de servicio','due_date':'2026-11-10','amount':None,'responsible_person_id':self.person.id,'next_action':'Consultar períodos adeudados'})
        self.assertIsNone(reminder.amount)
        self.assertEqual(db.session.query(RentCharge).count(),0)

if __name__=='__main__':unittest.main()
