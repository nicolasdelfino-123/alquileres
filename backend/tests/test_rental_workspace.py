import io
import json
import tempfile
import unittest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import patch
from cryptography.fernet import Fernet
from sqlalchemy import select
from app import create_app
from app.extensions import db
from app.models import User
from app.models.communication_model import Communication
from app.services.communication_service import process_one


class RentalWorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.app=create_app({'TESTING':True,'AUTH_RATE_LIMIT_ENABLED':False,'SQLALCHEMY_DATABASE_URI':'sqlite:///:memory:',
            'JWT_SECRET_KEY':'workspace-test-secret-at-least-32-bytes','MAIL_ENCRYPTION_KEY':Fernet.generate_key().decode(),
            'SMTP_HOST':'smtp.example.invalid','SMTP_USERNAME':'app@example.com','SMTP_PASSWORD':'test','SMTP_FROM':'app@example.com'})
        self.app.instance_path=self.directory.name
        self.context=self.app.app_context();self.context.push();db.create_all()
        admin=User(username='admin',email='admin@example.com',role='admin');admin.set_password('synthetic-password-123');db.session.add(admin);db.session.commit()
        self.client=self.app.test_client();token=self.client.post('/api/auth/login',json={'username':'admin','password':'synthetic-password-123'}).json['access_token'];self.client.environ_base['HTTP_AUTHORIZATION']='Bearer '+token
        self.owner=self.post('/persons',{'first_name':'Propietario','last_name':'Prueba','bank_alias':'alias.prueba','email':'owner@example.com'})
        self.tenant=self.post('/persons',{'first_name':'Inquilino','last_name':'Prueba','email':'tenant@example.com'})
        self.guarantor=self.post('/persons',{'first_name':'Garante','last_name':'Prueba','phone':'5493511234567'})
        self.property=self.post('/properties',{'address':'Dirección sintética 123','unit':'1A','property_type':'Departamento','ownerships':[{'person_id':self.owner['id'],'ownership_percentage':'100'}]})
        self.contract=self.post('/contracts',{'property_id':self.property['id'],'tenant_id':self.tenant['id'],'guarantor_ids':[self.guarantor['id']],
            'start_date':'2026-01-01','end_date':'2027-12-31','initial_rent':'1000000','current_rent':'1000000','payment_day':9,
            'administration_percentage':'8','adjustment_frequency_months':3,'adjustment_index':'IPC','collection_alias':'cuenta.cobros'})

    def tearDown(self):
        db.session.remove();db.drop_all();self.context.pop();self.directory.cleanup()

    def post(self,path,body,status=201):
        response=self.client.post('/api'+path,json=body)
        self.assertEqual(response.status_code,status,response.json)
        return response.json

    def generate(self):
        return self.post('/charges/generate',{'year':2026,'month':1,'currency':'ARS'},200)

    def test_optional_fields_guarantors_and_atomic_generation(self):
        self.assertEqual(self.property['price'],'0.00')
        self.assertEqual(self.contract['guarantor_ids'],[self.guarantor['id']])
        self.assertEqual(self.property['ownerships'][0]['person_id'],self.owner['id'])
        before=self.client.get('/api/workspace?year=2026&month=1&currency=ARS').json
        self.assertEqual(before['rows'][0]['status'],'not_generated')
        self.assertEqual(Decimal(before['summary']['pending']),Decimal('0'))
        self.assertEqual(len(self.generate()['created']),1)
        self.assertEqual(self.generate()['created'],[])
        charges=self.client.get('/api/charges').json
        self.assertEqual(len(charges),1);self.assertEqual(charges[0]['due_date'],'2026-01-09')
        response=self.client.put(f"/api/properties/{self.property['id']}",json={'ownerships':[{'person_id':self.owner['id'],'ownership_percentage':'120'}]})
        self.assertEqual(response.status_code,400)
        response=self.client.get(f"/api/properties/{self.property['id']}")
        self.assertEqual(response.json['ownerships'][0]['ownership_percentage'],'100.00')

    def test_collections_settlement_transfer_and_reporting(self):
        charge=self.post('/charges',{'contract_id':self.contract['id'],'period_year':2026,'period_month':1,'due_date':'2026-01-09','other_charges':'100000'})
        payment=self.post('/payments',{'contract_id':self.contract['id'],'charge_id':charge['id'],'amount':'1100000','payment_date':'2026-01-09','payment_method':'transfer','reference':'TEST-1','idempotency_key':'test-payment'})
        settlement=self.post('/settlements',{'property_id':self.property['id'],'owner_id':self.owner['id'],'period_year':2026,'period_month':1,'settlement_date':'2026-01-10','currency':'ARS','deductions':'10000','idempotency_key':'test-settlement'})
        self.assertEqual(settlement['administration_fee'],'80000.00')
        self.assertEqual(settlement['net_amount'],'1010000.00')
        transfer=self.post('/transfers',{'settlement_id':settlement['id'],'amount':'1010000','transfer_date':'2026-01-10','payment_method':'transfer','reference':'TEST-T1','idempotency_key':'test-transfer'})
        confirmed=self.post(f"/transfers/{transfer['id']}/confirm",{},200)
        self.assertTrue(confirmed['confirmed_at'])
        view=self.client.get('/api/workspace?year=2026&month=1&currency=ARS').json
        self.assertEqual(view['summary']['collected'],'1100000.00')
        self.assertEqual(view['summary']['transferred'],'1010000.00')
        self.post('/expenses',{'expense_date':'2026-01-15','category':'Teléfono','description':'Gasto sintético del negocio','amount':'15000','currency':'ARS','responsible_party':'agency'})
        report=self.client.get('/api/reports/business?year=2026&currency=ARS').json
        self.assertEqual(report['months'][0]['result'],'65000.00')
        self.assertEqual(report['months'][0]['fees'],'80000.00')

    def test_ipc_compounds_and_preserves_history(self):
        self.generate()
        adjustment=self.post(f"/contracts/{self.contract['id']}/apply-adjustment",{'effective_date':'2026-04-01','mode':'IPC','monthly_percentages':['2','3','4'],'source_url':'https://www.indec.gob.ar'},200)
        self.assertEqual(adjustment['new_amount'],'1092624.00')
        self.assertEqual(json.loads(adjustment['calculation_detail'])['monthly_percentages'],['2','3','4'])
        self.assertEqual(self.client.get('/api/charges').json[0]['rent_amount'],'1000000.00')
        self.post('/charges/generate',{'year':2026,'month':5,'currency':'ARS'},200)
        self.assertEqual(self.client.get('/api/charges?period_month=5').json[0]['rent_amount'],'1092624.00')
        self.post(f"/contracts/{self.contract['id']}/apply-adjustment",{'effective_date':'2026-05-01','mode':'percentage','percentage':'5'},409)

    def test_icl_ratio_and_validation(self):
        self.post(f"/contracts/{self.contract['id']}/apply-adjustment",{'effective_date':'2026-04-01','mode':'ICL','index_start':'10','index_end':'12'},200)
        self.assertEqual(self.client.get(f"/api/contracts/{self.contract['id']}/adjustments").json[0]['new_amount'],'1200000.00')
        self.post(f"/contracts/{self.contract['id']}/apply-adjustment",{'effective_date':'2026-07-01','mode':'ICL','index_start':'0','index_end':'12'},400)
        self.post('/contracts',{'property_id':self.property['id'],'tenant_id':self.tenant['id'],'guarantor_ids':[self.tenant['id']],
            'start_date':'2028-01-01','end_date':'2029-01-01','initial_rent':'1','current_rent':'1'},400)

    def test_attachments_are_private_and_validate_content(self):
        data={'property_id':str(self.property['id']),'contract_id':str(self.contract['id']),'document_type':'Contrato','file':(io.BytesIO(b'%PDF-1.4\nsynthetic-document'),'contract.pdf')}
        response=self.client.post('/api/files',data=data,content_type='multipart/form-data')
        self.assertEqual(response.status_code,201,response.json)
        document=response.json
        response=self.client.get(f"/api/files/{document['id']}")
        self.assertEqual(response.status_code,200)
        response.close()
        self.assertEqual(self.app.test_client().get(f"/api/files/{document['id']}").status_code,401)
        response=self.client.post('/api/files',data={'file':(io.BytesIO(b'<script>test</script>'),'fake.pdf')},content_type='multipart/form-data')
        self.assertEqual(response.status_code,400)

    def test_scheduled_email_is_durable_encrypted_and_cancellable(self):
        job=self.post(f"/contracts/{self.contract['id']}/messages",{'person_id':self.tenant['id'],'message':'Aviso sintético de prueba','scheduled_at':datetime.now(timezone.utc).isoformat()})
        stored=db.session.get(Communication,job['id'])
        self.assertNotIn('tenant@example.com',stored.payload)
        with patch('app.services.communication_service.deliver') as deliver:
            self.assertTrue(process_one());self.assertEqual(deliver.call_count,1)
        self.assertEqual(stored.status,'sent');self.assertIsNone(stored.payload)
        response=self.client.get(f"/api/contracts/{self.contract['id']}/messages")
        self.assertEqual(response.json[0]['status'],'sent');self.assertNotIn('payload',response.json[0])
        pending=self.post(f"/contracts/{self.contract['id']}/messages",{'person_id':self.owner['id'],'message':'Aviso sintético','scheduled_at':datetime.now(timezone.utc).isoformat()})
        self.post(f"/messages/{pending['id']}/cancel",{},200)
        with patch('app.services.communication_service.deliver') as deliver:
            self.assertFalse(process_one());deliver.assert_not_called()

    def test_charge_correction_keeps_audit_and_stops_after_payment(self):
        from app.models.charge_revision_model import ChargeRevision
        self.generate()
        charge=self.client.get('/api/charges').json[0]
        corrected=self.post(f"/charges/{charge['id']}/correct",{'other_charges':'500','reason':'Cargo documentado del período'},200)
        self.assertEqual(corrected['total_amount'],'1000500.00')
        audit=db.session.scalar(select(ChargeRevision))
        self.assertEqual(audit.previous_data['other_charges'],'0.00')
        self.assertEqual(Decimal(audit.new_data['other_charges']),Decimal('500.00'))
        self.post('/payments',{'contract_id':self.contract['id'],'charge_id':charge['id'],'amount':'1','payment_date':'2026-01-09','payment_method':'cash','reference':'payment-block-change','idempotency_key':'payment-block-change'})
        self.post(f"/charges/{charge['id']}/correct",{'other_charges':'600','reason':'No debe permitirse luego de cobrar'},409)

    def test_bulk_settlement_replays_without_duplicating(self):
        self.generate()
        charge=self.client.get('/api/charges').json[0]
        self.post('/payments',{'contract_id':self.contract['id'],'charge_id':charge['id'],'amount':'1000000','payment_date':'2026-01-09','payment_method':'cash','reference':'bulk-payment','idempotency_key':'bulk-payment'})
        body={'year':2026,'month':1,'currency':'ARS','owner_id':self.owner['id'],'idempotency_key':'bulk-owner-test'}
        first=self.post('/settlements/generate-owner',body,200)
        second=self.post('/settlements/generate-owner',body,200)
        self.assertEqual(first['settlements'][0]['id'],second['settlements'][0]['id'])
        self.assertEqual(len(self.client.get('/api/settlements').json),1)

    def test_sales_can_record_the_clients_spreadsheet_without_unknown_buyers(self):
        record=self.post('/sales',{'operation_description':'Operación sintética de archivo','agent_name':'Pako',
            'price':'100000','commission':'3000','agency_commission':'2000','personal_commission':'1000','currency':'USD',
            'sale_date':'2026-01-10','status':'completed','lead_source':'Fuente sintética','shared_with':'Otro agente'})
        self.assertIsNone(record['buyer_id'])
        self.assertIsNone(record['property_id'])
        self.assertEqual(record['agency_commission'],'2000.00')

    def test_archive_upload_preserves_source_without_creating_movements(self):
        from zipfile import ZipFile
        workbook=io.BytesIO()
        with ZipFile(workbook,'w') as archive:
            archive.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="JUNIO" sheetId="1" r:id="rId1"/></sheets></workbook>')
            archive.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
            archive.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="9"><c r="B9" t="inlineStr"><is><t>PROPIETARIO</t></is></c><c r="C9" t="inlineStr"><is><t>DOMICILIO</t></is></c></row><row r="10"><c r="B10" t="inlineStr"><is><t>Propietario sintético</t></is></c></row><row r="11"><c r="C11" t="inlineStr"><is><t>Dirección sintética 1</t></is></c></row></sheetData></worksheet>')
        workbook.seek(0)
        response=self.client.post('/api/archive',data={'file':(workbook,'source.xlsx')},content_type='multipart/form-data')
        self.assertEqual(response.status_code,200,response.json)
        source=self.client.get('/api/archive/sheet?name=JUNIO').json
        self.assertEqual(source['rows'][0]['values']['B'],'Propietario sintético')
        self.assertEqual(len(self.client.get('/api/contracts').json),1)
        self.assertEqual(self.client.get('/api/payments').json,[])

    def test_employee_cannot_access_ledger_or_workbook(self):
        employee=User(username='employee',email='employee@example.com',role='operator')
        employee.set_password('employee-password-123');db.session.add(employee);db.session.commit()
        client=self.app.test_client()
        token=client.post('/api/auth/login',json={'username':'employee','password':'employee-password-123'}).json['access_token']
        client.environ_base['HTTP_AUTHORIZATION']='Bearer '+token
        self.assertEqual(client.get('/api/properties').status_code,200)
        self.assertEqual(client.get('/api/archive').status_code,403)
        self.assertEqual(client.get('/api/workspace?year=2026&month=1&currency=ARS').status_code,403)

    def test_monthly_receipt_upload_and_real_email_attachment(self):
        content=b'%PDF-1.4\nreceipt-for-test\n%%EOF'
        uploaded=self.client.post('/api/files',data={'contract_id':str(self.contract['id']),'property_id':str(self.property['id']),
            'document_type':'Comprobante de gas','period_year':'2026','period_month':'11','file':(io.BytesIO(content),'gas-noviembre.pdf')},content_type='multipart/form-data')
        self.assertEqual(uploaded.status_code,201,uploaded.json)
        document=uploaded.json
        self.assertEqual(document['period_month'],11)
        filtered=self.client.get(f"/api/documents?contract_id={self.contract['id']}&period_year=2026&period_month=11").json
        self.assertEqual([row['id'] for row in filtered],[document['id']])
        scheduled=self.post(f"/contracts/{self.contract['id']}/messages",{'person_id':self.tenant['id'],'message':'Comprobante del período',
            'scheduled_at':datetime.now(timezone.utc).isoformat(),'document_ids':[document['id']]})
        with patch('app.services.communication_service.deliver') as deliver:
            self.assertTrue(process_one())
            message=deliver.call_args.args[0]
            attachments=list(message.iter_attachments())
            self.assertEqual(len(attachments),1)
            self.assertEqual(attachments[0].get_filename(),'gas-noviembre.pdf')
            self.assertEqual(attachments[0].get_payload(decode=True),content)
        self.assertEqual(db.session.get(Communication,scheduled['id']).status,'sent')

    def test_attachments_reject_other_clients_and_invalid_period(self):
        other=self.post('/properties',{'address':'Otra propiedad sintética'})
        document=self.post('/documents',{'property_id':other['id'],'document_type':'Ajeno','file_path':'https://example.invalid/document.pdf','original_filename':'ajeno.pdf'})
        self.post(f"/contracts/{self.contract['id']}/messages",{'person_id':self.tenant['id'],'message':'No enviar',
            'scheduled_at':datetime.now(timezone.utc).isoformat(),'document_ids':[document['id']]},400)
        bad=self.client.post('/api/files',data={'contract_id':str(self.contract['id']),'period_year':'2026','period_month':'13','file':(io.BytesIO(b'%PDF-1.4\ntest'),'test.pdf')},content_type='multipart/form-data')
        self.assertEqual(bad.status_code,400)

    def test_scheduled_attachment_is_not_silently_replaced(self):
        from pathlib import Path
        document=self.client.post('/api/files',data={'contract_id':str(self.contract['id']),'file':(io.BytesIO(b'%PDF-1.4\noriginal'),'receipt.pdf')},content_type='multipart/form-data').json
        self.post(f"/contracts/{self.contract['id']}/messages",{'person_id':self.tenant['id'],'message':'Adjunto',
            'scheduled_at':datetime.now(timezone.utc).isoformat(),'document_ids':[document['id']]})
        (Path(self.app.instance_path)/'documents'/document['file_path']).write_bytes(b'%PDF-1.4\nchanged')
        with patch('app.services.communication_service.deliver') as deliver:
            process_one()
            deliver.assert_not_called()
