"""Manual scenario refresh for the original seed only; never startup code.

All invented values remain documented in the private instance manifest.
"""
import json
import os
import sys
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));os.chdir(ROOT)
from dotenv import dotenv_values
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from app import create_app
from app.extensions import db
from app.models import Property, Person, RentalContract, Reminder, Expense, RentCharge, RentPayment, OwnerSettlement, OwnerTransfer
from app.models.common import business_today, utcnow
from app.services.management_service import ManagementService, FinanceService, money
from app.services.utility_service import validate_rules
from seed_demo_once import backup

NAMES=[('Camila','Suárez'),('Martín','Acosta'),('Lucía','Benítez'),('Diego','Romero'),('Sofía','Medina'),('Pablo','Castro'),('Valentina','Ríos'),('Nicolás','Herrera'),('Florencia','Molina'),('Federico','Pereyra'),('Julieta','Navarro'),('Lucas','Torres'),('Carolina','Aguirre'),('Santiago','Vega'),('Mariana','Cabrera'),('Sebastián','Luna'),('Agustina','Sosa'),('Gonzalo','Figueroa'),('Paula','Godoy'),('Matías','Peralta'),('Daniela','Ortiz'),('Ignacio','Ferreyra'),('Rocío','Vargas'),('Emiliano','Díaz')]


def main():
    manifest=ROOT/'instance/seeds/portfolio-scenario-v2.json'
    if manifest.exists() and json.loads(manifest.read_text()).get('complete'):
        print('La cartera de simulación ya fue actualizada; no se duplicaron registros.');return
    parsed=make_url(dotenv_values(ROOT/'.env')['DATABASE_URL'])
    if parsed.get_backend_name()!='postgresql' or parsed.host not in {'localhost','127.0.0.1',None}:
        raise RuntimeError('Solo se admite PostgreSQL local.')
    app=create_app({'MAIL_WORKER_AUTOSTART':False})
    with app.app_context():
      lock=db.engine.connect()
      try:
        lock.execute(text('SELECT pg_advisory_lock(871624103)'))
        if manifest.exists() and json.loads(manifest.read_text()).get('complete'):return
        properties=list(db.session.scalars(select(Property).where(Property.internal_code.like('DEMO-PAKO-V1-%')).order_by(Property.id)))
        if len(properties)!=26:raise RuntimeError('La cartera original no coincide; no se modificó nada.')
        backup(parsed)
        today=business_today();counts=Counter();ids={'properties':[p.id for p in properties],'persons':[],'contracts':[],'reminders':[],'expenses':[]}
        manifest.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        provenance={'complete':False,'date':today.isoformat(),'notice':'SIMULACIÓN. Nombres de inquilinos, identificadores, condiciones, fechas e importes de servicios inventados por pedido del usuario. Propiedades y propietarios del Excel. No usar como contabilidad real. Contactos sin envío real.','ids':ids}
        manifest.write_text(json.dumps(provenance,ensure_ascii=False,indent=2))
        create=ManagementService.create.__wrapped__
        reminders=list(db.session.scalars(select(Reminder).where(Reminder.property_id.in_(ids['properties']))))
        originals=[r for r in reminders if (r.title or '').startswith('DEMO') and 'DEMO:' in (r.description or '')]
        tenant_index=0;changed_people=set()
        offsets=[-3,4,18,45,80,150,240,320]
        task_offsets=[-18,-7,-2,0,1,3,6,12,22,40]
        for index,prop in enumerate(properties):
            prop.title=' '.join(filter(None,[prop.address,prop.unit]));prop.internal_code=f'BR-{index+1:03}'
            prop.notes='Administración de alquileres. Consultar condiciones y pendientes en la ficha del contrato.'
            counts['propiedades']+=1
            owners=[link.person for link in prop.owners]
            for owner in owners:
                if owner.id in changed_people:continue
                changed_people.add(owner.id);ids['persons'].append(owner.id)
                if 'DEMO' in (owner.notes or ''):owner.notes='Propietario vinculado a la cartera de administración.'
                owner.bank_alias=f'bricks.propietario.{owner.id}'
            contracts=list(db.session.scalars(select(RentalContract).where(RentalContract.property_id==prop.id).order_by(RentalContract.id)))
            seed_contracts=[c for c in contracts if 'DEMO:' in (c.notes or '')]
            # Only original seed contracts and their tagged movements are altered.
            for contract in seed_contracts:
                ids['contracts'].append(contract.id);counts['contratos']+=1
                tenant=db.session.get(Person,contract.tenant_id)
                first,last=NAMES[tenant_index%len(NAMES)];tenant_index+=1
                tenant.first_name,tenant.last_name=first,last
                candidate=str(48000000+tenant.id*137)
                if not db.session.scalar(select(Person.id).where(Person.dni==candidate,Person.id!=tenant.id)):tenant.dni=candidate
                tenant.email=f'contacto.{tenant.id}@example.invalid';tenant.phone=None;tenant.address=prop.address
                tenant.occupation=['Administrativo','Docente','Comerciante','Profesional independiente'][index%4]
                tenant.notes='Contacto principal del contrato de alquiler.';changed_people.add(tenant.id);ids['persons'].append(tenant.id)
                end=today+timedelta(days=offsets[index%len(offsets)])
                contract.start_date=date(today.year-1,1+(index%10),1)
                contract.end_date=end;contract.status='expired' if end<today else 'active'
                contract.payment_day=[1,3,5,7,10,12,15,20,25,28][index%10]
                contract.signed_date=contract.start_date-timedelta(days=3)
                contract.adjustment_index='Porcentaje pactado';contract.fixed_adjustment_percentage=Decimal('5.00')
                contract.next_adjustment_date=min(today+timedelta(days=[2,9,24,50,95][index%5]),end) if end>today else None
                contract.notes=['Municipal a cargo del inquilino. Solicitar comprobantes mensuales.','Rentas a cargo del propietario; coordinar pago antes de liquidar.','Controlar servicios y registrar los comprobantes del período.'][index%3]
                contract.collection_alias=f'bricks.cobros.{contract.id}'
                custom='custom:'+f'{contract.id:032x}'
                rules=[{'service':'municipal','payer':'tenant','management':'collect_pay' if index%2 else 'direct','frequency':'monthly','day':[5,10,15,20][index%4],'reference':f'MUN-{450000+index*37}','reference_amount':str(18500+index*670),'notes':'Solicitar boleta del período y verificar el pago.'},
                       {'service':'provincial','payer':'owner','management':'pay_deduct','frequency':'monthly','day':[7,12,18,25][index%4],'reference':f'DGR-{700000+index*19}','reference_amount':str(12900+index*410),'notes':'Pagar y dejar comprobante para la liquidación del propietario.'},
                       {'service':'electricity' if index%2 else 'gas','payer':'tenant','management':'collect_pay','frequency':'monthly','day':[8,14,21,27][index%4],'reference':f'CTA-{900000+index*51}','reference_amount':str(24300+index*930),'notes':'Confirmar importe de la factura antes de cobrar.'}]
                if index%3==0:rules.append({'service':custom,'name':'Personal Flow','payer':'tenant','management':'collect_pay','frequency':'monthly','day':16,'reference':f'FLOW-{330000+index}','reference_amount':str(28500+index*300),'notes':'Abonar el servicio y guardar el comprobante.'})
                if index%4==0:rules.append({'service':'expenses_regular','payer':'tenant','management':'collect_pay','frequency':'monthly','day':10,'reference':f'MP {3990100+index}','reference_amount':str(65500+index*1100),'notes':'Pagar expensas por Mercado Pago. Verificar si existen extraordinarias.'})
                contract.utility_rules=validate_rules(rules);prop.utility_rules=validate_rules(rules)
                for rule in rules:
                    legacy={'municipal':'utility_municipal','provincial':'utility_provincial','electricity':'utility_electricity','gas':'utility_gas'}.get(rule['service'])
                    if legacy:setattr(prop,legacy,rule['reference'])
                # Retain the original financial amounts and associations.
                seeded_charges=[c for c in contract.charges if 'DEMO:' in (c.notes or '')]
                for charge in seeded_charges:
                    due=date(charge.period_year,charge.period_month,min(contract.payment_day,28))
                    charge.due_date=min(due,end);charge.notes='Mensualidad de alquiler. Verificar saldo y comprobantes.'
                    for payment in charge.payments:
                        if not payment.idempotency_key.startswith('DEMO-PAKO-V1-'):continue
                        payment.payment_date=min(today-timedelta(days=index%7),end)
                        payment.reference=f'COB-{payment.payment_date:%Y%m%d}-{payment.id:05}'
                        payment.payment_method='cash' if index%5==0 else 'transfer';payment.notes='Cobro de alquiler recibido.'
                    charge.status=charge.calculated_status
                for settlement in prop.settlements:
                    if not settlement.idempotency_key.startswith('DEMO-PAKO-V1-'):continue
                    seed_payments=[p for c in seeded_charges if c.period_year==settlement.period_year and c.period_month==settlement.period_month for p in c.payments if not p.cancelled_at]
                    settlement.settlement_date=max([p.payment_date for p in seed_payments] or [today])
                    settlement.notes='Liquidación de alquileres cobrados; honorarios según contrato.'
                    for transfer in settlement.transfers:
                        if not transfer.idempotency_key.startswith('DEMO-PAKO-V1-'):continue
                        transfer.transfer_date=min(today,settlement.settlement_date+timedelta(days=index%3))
                        transfer.reference=f'TRF-{transfer.transfer_date:%Y%m%d}-{transfer.id:05}';transfer.payment_method='transfer';transfer.notes='Transferencia al propietario por liquidación mensual.'
                tasks=[
                    ('Cobrar Municipal al inquilino','Servicio / control',Decimal(18500+index*670),tenant.id,'Solicitar boleta, cobrar junto al alquiler y guardar comprobante.'),
                    ('Pagar Rentas y descontar al propietario','Servicio / control',Decimal(12900+index*410),owners[0].id if owners else None,'Consultar la boleta y registrar el pago antes de liquidar.'),
                    ('Cobrar luz y gas del mes','Servicio / control',Decimal(42000+index*850),tenant.id,'Confirmar las facturas del período y pedir comprobante.'),
                    ('Pagar Personal Flow','Servicio / control',Decimal(28500+index*300),tenant.id,'Cobrar el servicio al inquilino y abonar antes del vencimiento.'),
                    ('Verificar deuda de agua y luz','Deuda de servicio',None,tenant.id,'Consultar períodos adeudados y acordar fecha de regularización.'),
                    ('Arreglar vidrio y colocar pasador de ventana','Mantenimiento',Decimal(48000+index*1200),owners[0].id if owners else None,'Coordinar visita con el inquilino y pedir presupuesto al proveedor.'),
                    ('Pedir contrato firmado y completar ACM','Contrato / firma',None,owners[0].id if owners else None,'Contactar al propietario y adjuntar el contrato firmado.'),
                    ('Pagar expensas por Mercado Pago','Expensas',Decimal(65500+index*1100),tenant.id,f'Verificar liquidación del consorcio. Código de pago: {3990100+index}.'),
                    ('Reclamar saldo pendiente del alquiler','Alquiler',None,tenant.id,'Revisar el saldo de la mensualidad y coordinar fecha de pago.'),
                    ('Confirmar transferencia al propietario','Alquiler',None,owners[0].id if owners else None,'Verificar liquidación y comprobante de transferencia antes de confirmar.'),
                ]
                # Two complementary actions per contract, with staggered dates.
                for position in range(2):
                    title,category,amount,responsible,action=tasks[(index+position*3)%len(tasks)]
                    due=today+timedelta(days=task_offsets[(index+position*4)%len(task_offsets)])
                    key=f'portfolio:v2:{contract.id}:{position}'
                    body={'property_id':prop.id,'contract_id':contract.id,'title':title,'description':f'{prop.address} {prop.unit or ""}. Período {today.month:02}/{today.year}.','due_date':due.isoformat(),'category':category,'priority':'urgent' if due<=today else 'normal','progress':'in_progress' if index%4==0 else 'pending','amount':str(amount) if amount is not None else None,'responsible_person_id':responsible,'next_action':action}
                    if originals:
                        reminder=originals.pop(0)
                        for field,value in body.items():setattr(reminder,field,date.fromisoformat(value) if field=='due_date' else Decimal(value) if field=='amount' and value is not None else value)
                    else:reminder=create('reminders',body)
                    reminder.source_key=key
                    if index%11==0 and position==1:
                        reminder.status='completed';reminder.completed_at=utcnow()
                    ids['reminders'].append(reminder.id);counts['recordatorios']+=1
                # A distinct property expense every few contracts; no fictitious
                # deductions are applied to existing owner settlements.
                if index%5==0:
                    expense=create('expenses',{'property_id':prop.id,'contract_id':contract.id,'expense_date':(today-timedelta(days=index%7)).isoformat(),'category':'Mantenimiento','description':['Reparación de cerradura','Reposición de vidrio','Revisión de instalación de gas'][index%3],'amount':str(28500+index*1750),'currency':'ARS','responsible_party':'owner' if index%2 else 'tenant','notes':'Comprobante pendiente de adjuntar.'})
                    ids['expenses'].append(expense.id);counts['gastos']+=1
        for expense in db.session.scalars(select(Expense).where(Expense.category=='Oficina (DEMO)')):
            if 'ficticio' in (expense.description or ''):
                expense.category='Alquiler de oficina';expense.description='Alquiler de oficina - noviembre';expense.expense_date=today-timedelta(days=3);expense.notes='Gasto operativo mensual de la inmobiliaria.'
        for old in originals:
            old.title='Revisar documentación de la propiedad';old.description='Verificar contrato firmado y comprobantes de servicios.';old.next_action='Revisar la ficha y completar la documentación faltante.';old.due_date=today+timedelta(days=6)
        db.session.flush()
        # Verify the refreshed scenario before committing it.
        for contract_id in ids['contracts']:
            contract=db.session.get(RentalContract,contract_id)
            assert contract.start_date<contract.end_date
            for charge in contract.charges:
                assert contract.start_date<=charge.due_date<=contract.end_date
                assert charge.outstanding_balance>=0
        for prop in properties:
            for settlement in prop.settlements:
                assert settlement.net_amount==settlement.gross_amount-settlement.administration_fee-settlement.deductions
                assert settlement.outstanding_balance>=0
                for transfer in settlement.transfers:assert settlement.settlement_date<=transfer.transfer_date<=today
        db.session.commit()
        provenance['complete']=True;provenance['counts']=dict(counts);manifest.write_text(json.dumps(provenance,ensure_ascii=False,indent=2))
        print('Cartera de simulación actualizada: '+', '.join(f'{n} {label}' for label,n in counts.items()))
        print('Fechas y responsables variados; importes contables originales conservados. Backup y procedencia privados guardados.')
      except Exception:
        db.session.rollback();raise
      finally:
        lock.execute(text('SELECT pg_advisory_unlock(871624103)'));lock.close()

if __name__=='__main__':
    mask=os.umask(0o077)
    try:main()
    finally:os.umask(mask)
