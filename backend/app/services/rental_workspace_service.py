"""Operational views backed by recorded contracts, charges and money movements."""
import calendar
import json
from datetime import date
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import (Property, Person, PropertyOwner, RentalContract, RentAdjustment,
                        RentCharge, RentPayment, OwnerSettlement, OwnerTransfer, Expense, Document, Reminder)
from app.models.common import business_today, ZERO, utcnow
from app.services.management_service import (APIError, FinanceService, ManagementService, get_record,
                                               serialize, money, transactional, convert)
from app.services.report_service import period_arguments, add_months, integer


def rent_on(contract, day):
    adjustments = sorted(contract.adjustments, key=lambda a: (a.effective_date, a.id))
    applicable = [a for a in adjustments if a.effective_date <= day]
    return applicable[-1].new_amount if applicable else adjustments[0].previous_amount if adjustments else contract.current_rent


def next_adjustment(contract):
    if contract.next_adjustment_date:
        return contract.next_adjustment_date
    if not contract.adjustment_frequency_months:
        return None
    latest = max((item.effective_date for item in contract.adjustments), default=contract.start_date)
    value = add_months(latest, contract.adjustment_frequency_months)
    return value if value and value <= contract.end_date else None


def all_records(model):
    statement=select(model).order_by(model.id)
    if model is Property:
        statement=statement.options(selectinload(Property.owners))
    if model is RentalContract:
        statement=statement.options(selectinload(RentalContract.tenant_links),selectinload(RentalContract.guarantor_links),selectinload(RentalContract.adjustments))
    return list(db.session.scalars(statement))


class RentalWorkspaceService:
    @staticmethod
    def workspace(arguments):
        year, month, currency = period_arguments(arguments)
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        properties = all_records(Property)
        people = all_records(Person)
        owners = all_records(PropertyOwner)
        contracts = all_records(RentalContract)
        charges = list(db.session.scalars(select(RentCharge).options(selectinload(RentCharge.payments)).where(RentCharge.period_year == year, RentCharge.period_month == month, RentCharge.currency == currency)))
        payments = list(db.session.scalars(select(RentPayment).join(RentCharge, RentPayment.charge_id == RentCharge.id).where(RentCharge.period_year == year, RentCharge.period_month == month, RentCharge.currency == currency)))
        settlements = list(db.session.scalars(select(OwnerSettlement).options(selectinload(OwnerSettlement.transfers)).where(OwnerSettlement.period_year == year, OwnerSettlement.period_month == month, OwnerSettlement.currency == currency)))
        settlement_ids = [s.id for s in settlements]
        transfers = list(db.session.scalars(select(OwnerTransfer).where(OwnerTransfer.settlement_id.in_(settlement_ids)))) if settlement_ids else []
        documents = list(db.session.scalars(select(Document).order_by(Document.id.desc())))
        current = [c for c in contracts if c.currency == currency and c.start_date <= end and c.end_date >= start and c.status != 'cancelled']
        active_charges = [c for c in charges if not c.cancelled_at]
        rows = []
        for contract in current:
            charge = next((c for c in charges if c.contract_id == contract.id), None)
            adjustment = next_adjustment(contract)
            rows.append({'contract_id': contract.id, 'charge_id': charge.id if charge else None,
                'rent_amount': str(charge.rent_amount if charge else rent_on(contract, start)),
                'next_adjustment_date': adjustment.isoformat() if adjustment else None,
                'status': charge.calculated_status if charge else 'not_generated'})
        return {'year': year, 'month': month, 'currency': currency,
            'properties': [serialize(v) for v in properties], 'people': [serialize(v) for v in people],
            'owners': [serialize(v) for v in owners], 'contracts': [{**serialize(v), 'current_rent': str(rent_on(v, business_today()))} for v in contracts],
            'charges': [serialize(v) for v in charges], 'payments': [serialize(v) for v in payments],
            'settlements': [serialize(v) for v in settlements], 'transfers': [serialize(v) for v in transfers],
            'documents': [serialize(v) for v in documents], 'rows': rows,
            'summary': {'billed': str(sum((c.total_amount for c in active_charges), ZERO)),
                'collected': str(sum((c.paid_amount for c in active_charges), ZERO)),
                'pending': str(sum((c.outstanding_balance for c in active_charges), ZERO)),
                'fees': str(sum((s.administration_fee for s in settlements if not s.cancelled_at), ZERO)),
                'net': str(sum((s.net_amount for s in settlements if not s.cancelled_at), ZERO)),
                'transferred': str(sum((t.amount for t in transfers if not t.cancelled_at), ZERO)),
                'paid_properties': len({c.contract.property_id for c in active_charges if c.paid_amount > 0})}}

    @staticmethod
    @transactional
    def generate(data):
        year, month, currency = period_arguments(data)
        ids = data.get('contract_ids')
        if ids is not None and (not isinstance(ids, list) or len(ids) > 500 or any(type(v) is not int or v <= 0 for v in ids)):
            raise APIError('Seleccioná contratos válidos (máximo 500)')
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        contracts = list(db.session.scalars(select(RentalContract).where(RentalContract.status == 'active',
            RentalContract.currency == currency, RentalContract.start_date <= end, RentalContract.end_date >= start).order_by(RentalContract.property_id, RentalContract.id)))
        created, existing = [], []
        for contract in contracts:
            if ids is not None and contract.id not in ids:
                continue
            FinanceService.lock_property_for_contract(contract.id)
            charge = db.session.scalar(select(RentCharge).where(RentCharge.contract_id == contract.id, RentCharge.period_year == year, RentCharge.period_month == month))
            if charge:
                existing.append(charge.id)
                continue
            due = date(year, month, min(contract.payment_day or 10, end.day))
            due = min(max(due, contract.start_date), contract.end_date)
            charge = FinanceService.create_charges({'contract_id': contract.id, 'period_year': year, 'period_month': month,
                'due_date': due.isoformat(), 'rent_amount': str(rent_on(contract, start))})
            created.append(charge.id)
        return {'message': f'{len(created)} mensualidades generadas; {len(existing)} ya estaban registradas.', 'created': created, 'existing': existing}

    @staticmethod
    @transactional
    def adjust(identifier, data):
        contract = FinanceService.lock_property_for_contract(identifier)
        if contract.status != 'active':
            raise APIError('El contrato no está activo', 409)
        try:
            effective = date.fromisoformat(data.get('effective_date', ''))
        except (ValueError, TypeError):
            raise APIError('Ingresá una fecha de aplicación válida') from None
        if not contract.start_date <= effective <= contract.end_date:
            raise APIError('La fecha debe estar dentro del contrato')
        if effective.day != 1:
            raise APIError('El ajuste de mensualidades debe comenzar el primer día del mes')
        if any(a.effective_date >= effective for a in contract.adjustments):
            raise APIError('Ya existe un ajuste en esa fecha o posterior. Se conserva el historial.', 409)
        if any(not c.cancelled_at and date(c.period_year, c.period_month, 1) >= effective for c in contract.charges):
            raise APIError('Ya hay mensualidades generadas desde esa fecha. No se modifican importes registrados.', 409)
        base = rent_on(contract, effective)
        mode = data.get('mode', 'percentage')
        def number(value, field='adjustment_percentage'):
            column = RentAdjustment.__table__.c[field]
            return convert(column, value)
        if mode == 'amount':
            amount = number(data.get('new_amount'), 'new_amount')
            if amount is None:
                raise APIError('Ingresá el nuevo importe')
            factor = amount / base if base else Decimal('1')
            detail = {'mode': mode}
        elif mode == 'ICL':
            begin, finish = number(data.get('index_start')), number(data.get('index_end'))
            if begin is None or finish is None or begin <= 0 or finish <= 0:
                raise APIError('Cargá los valores ICL inicial y final de la fuente oficial')
            factor = finish / begin
            detail = {'mode': mode, 'initial': str(begin), 'final': str(finish)}
        elif mode == 'IPC':
            values = data.get('monthly_percentages')
            if not isinstance(values, list) or not 1 <= len(values) <= 36:
                raise APIError('Cargá las variaciones mensuales IPC del período, sin omitir meses')
            factor = Decimal('1')
            rates = []
            for value in values:
                rate = number(value)
                if rate is None:
                    raise APIError('Falta una variación mensual IPC')
                factor *= 1 + rate / 100
                rates.append(str(rate))
            detail = {'mode': mode, 'monthly_percentages': rates}
        elif mode == 'percentage':
            rate = number(data.get('percentage'))
            if rate is None:
                raise APIError('Ingresá el porcentaje acordado')
            factor = 1 + rate / 100
            detail = {'mode': mode, 'percentage': str(rate)}
        else:
            raise APIError('Método de ajuste inválido')
        amount = amount if mode == 'amount' else money(base * factor)
        if amount < base:
            raise APIError('El nuevo importe no puede ser menor al anterior en este formulario')
        rate = ((factor - 1) * 100).quantize(Decimal('.0001'))
        source = data.get('source_url')
        if source and (not isinstance(source, str) or len(source) > 500 or not source.startswith('https://')):
            raise APIError('La fuente debe ser una dirección HTTPS válida')
        detail['base'] = str(base)
        adjustment = RentAdjustment(contract_id=contract.id, effective_date=effective, previous_amount=base,
            new_amount=amount, adjustment_percentage=rate, index_name=mode if mode in {'IPC', 'ICL'} else contract.adjustment_index,
            calculation_detail=json.dumps(detail), source_url=source or None, notes=data.get('notes') or None)
        from app.services.management_service import validate
        validate(adjustment)
        db.session.add(adjustment)
        if effective <= business_today():
            contract.current_rent = amount
        if contract.adjustment_frequency_months:
            next_date = add_months(effective, contract.adjustment_frequency_months)
            contract.next_adjustment_date = next_date if next_date and next_date <= contract.end_date else None
        db.session.flush()
        return serialize(adjustment)

    @staticmethod
    @transactional
    def confirm_transfer(identifier):
        transfer = get_record(OwnerTransfer, identifier, lock=True)
        if transfer.cancelled_at:
            raise APIError('La transferencia está anulada', 409)
        transfer.confirmed_at = transfer.confirmed_at or utcnow()
        return serialize(transfer)

    @staticmethod
    def business(arguments):
        year = integer(arguments.get('year'), 'year', 1, 9998)
        currency = arguments.get('currency', 'ARS')
        period_arguments({'year':year, 'month':1, 'currency':currency})
        properties = {p.id:p for p in all_records(Property)}
        payments = list(db.session.scalars(select(RentPayment).options(selectinload(RentPayment.charge).selectinload(RentCharge.contract)).join(RentCharge, RentPayment.charge_id == RentCharge.id).where(
            RentPayment.payment_date >= date(year,1,1), RentPayment.payment_date < date(year+1,1,1),
            RentPayment.cancelled_at.is_(None), RentCharge.currency == currency)))
        expenses = list(db.session.scalars(select(Expense).where(Expense.expense_date >= date(year,1,1),
            Expense.expense_date < date(year+1,1,1), Expense.currency == currency)))
        rows=[]
        for month in range(1,13):
            receipts = [p for p in payments if p.payment_date.month == month]
            fees, own = ZERO, ZERO
            for payment in receipts:
                charge = payment.charge
                prop = properties[charge.contract.property_id]
                own_share = (prop.agency_ownership_percentage or ZERO) / 100
                # Only rent is an agency revenue basis. Utility reimbursements are excluded.
                rent_share = payment.amount * min(charge.rent_amount, charge.total_amount) / charge.total_amount if charge.total_amount else ZERO
                fees += rent_share * charge.administration_percentage / 100 * (1-own_share)
                own += rent_share * own_share
            spent = sum((e.amount for e in expenses if e.expense_date.month == month and e.responsible_party == 'agency'), ZERO)
            collected = sum((p.amount for p in receipts),ZERO)
            net = money(fees+own-spent)
            rows.append({'month':month,'properties':len({p.charge.contract.property_id for p in receipts}),
                'collected':str(money(collected)), 'fees':str(money(fees)), 'own_income':str(money(own)),
                'expenses':str(spent), 'result':str(net), 'margin':str(money(net/(fees+own)*100)) if fees+own else None})
        return {'year':year,'currency':currency,'months':rows}

    @staticmethod
    @transactional
    def settle_owner(data):
        year,month,currency=period_arguments(data)
        owner_id=integer(data.get('owner_id'),'owner_id',1,2147483647)
        links=list(db.session.scalars(select(PropertyOwner).where(PropertyOwner.person_id==owner_id).order_by(PropertyOwner.property_id)))
        created=[]
        key=data.get('idempotency_key')
        if not isinstance(key,str) or not 1<=len(key)<=50:
            raise APIError('Falta la referencia de la operación')
        for link in links:
            get_record(Property,link.property_id,lock=True)
            replay_key=f'{key}:{link.property_id}:{owner_id}'
            replay=db.session.scalar(select(OwnerSettlement).where(OwnerSettlement.idempotency_key==replay_key))
            if replay:
                if replay.period_year != year or replay.period_month != month or replay.currency != currency:
                    raise APIError('La referencia ya corresponde a otro período',409)
                if replay.cancelled_at:
                    raise APIError('La operación anterior fue anulada',409)
                created.append(serialize(replay))
                continue
            charges=list(db.session.scalars(select(RentCharge).join(RentalContract).where(RentalContract.property_id==link.property_id,
                RentCharge.period_year==year,RentCharge.period_month==month,RentCharge.currency==currency,RentCharge.cancelled_at.is_(None))))
            collected=sum((sum((p.amount for p in c.payments if not p.cancelled_at and p.payment_date<=business_today()),ZERO) for c in charges),ZERO)
            prior=FinanceService.active_settlements(link.property_id,year,month,currency)
            available=min(collected-sum((s.gross_amount for s in prior),ZERO),money(collected*link.ownership_percentage/100)-sum((s.gross_amount for s in prior if s.owner_id==owner_id),ZERO))
            if available<=0:
                continue
            record=FinanceService.create_settlements({'property_id':link.property_id,'owner_id':owner_id,'period_year':year,
                'period_month':month,'currency':currency,'settlement_date':business_today().isoformat(),'idempotency_key':replay_key})
            created.append(serialize(record))
        return {'message':f'{len(created)} liquidaciones registradas sobre cobros disponibles.','settlements':created}

    @staticmethod
    @transactional
    def correct_charge(identifier,data,creator_id):
        from app.models.charge_revision_model import ChargeRevision
        from app.services.management_service import payload,validate
        record=get_record(RentCharge,identifier)
        FinanceService.lock_property_for_contract(record.contract_id)
        record=get_record(RentCharge,identifier,lock=True)
        if record.cancelled_at or record.payments or FinanceService.active_settlements(record.contract.property_id,record.period_year,record.period_month,record.currency):
            raise APIError('Esta mensualidad ya tiene movimientos o está anulada; se conserva su historial.',409)
        reason=data.get('reason')
        if not isinstance(reason,str) or not 5<=len(reason.strip())<=500:
            raise APIError('Ingresá un motivo de corrección de entre 5 y 500 caracteres')
        allowed={'rent_amount','other_charges','discounts','due_date','notes'}
        if set(data)-allowed-{'reason'}:
            raise APIError('Campo de corrección no admitido')
        fields=payload(RentCharge,{key:value for key,value in data.items() if key!='reason'})
        previous={key:serialize(record)[key] for key in allowed}
        for key,value in fields.items():setattr(record,key,value)
        record.total_amount=record.rent_amount+record.other_charges-record.discounts
        if record.total_amount<0:raise APIError('Los descuentos superan la mensualidad')
        if not record.contract.start_date<=record.due_date<=record.contract.end_date:
            raise APIError('El vencimiento debe estar dentro del contrato')
        validate(record)
        record.status=record.calculated_status
        db.session.add(ChargeRevision(charge_id=record.id,created_by_id=creator_id,reason=reason.strip(),
            previous_data=previous,new_data={key:serialize(record)[key] for key in allowed}))
        db.session.flush()
        return serialize(record)
