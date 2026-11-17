from datetime import date
from decimal import Decimal, InvalidOperation
from flask import g
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.extensions import db
from app.models import RentalContract, ContractFee, ContractFeePayment
from app.models.common import ZERO, business_today, utcnow
from app.services.management_service import APIError, get_record, serialize, transactional


def amount(value):
    try:
        result = Decimal(str(value))
        if isinstance(value, bool) or not result.is_finite() or result <= 0 or result >= Decimal('10000000000') or result != result.quantize(Decimal('.01')):
            raise ValueError()
        return result
    except (InvalidOperation, ValueError):
        raise APIError('Ingresá un importe positivo con hasta dos decimales') from None


def day(value):
    try:
        result = date.fromisoformat(value)
        if result > business_today():
            raise ValueError()
        return result
    except (ValueError, TypeError):
        raise APIError('Ingresá una fecha válida, no futura') from None


def public(fee):
    paid = sum((p.amount for p in fee.payments if not p.cancelled_at), ZERO)
    return {**serialize(fee), 'paid_amount': str(paid), 'pending_amount': str(ZERO if fee.cancelled_at else fee.amount - paid),
            'payments': [serialize(p) for p in sorted(fee.payments, key=lambda p: p.id)]}


def listing(identifier):
    get_record(RentalContract, identifier)
    return [public(fee) for fee in db.session.scalars(select(ContractFee).options(selectinload(ContractFee.payments)).where(ContractFee.contract_id == identifier).order_by(ContractFee.id))]


@transactional
def create(identifier, data):
    contract = get_record(RentalContract, identifier, lock=True)
    if set(data) - {'amount', 'currency', 'payer', 'agreed_date', 'notes'}:
        raise APIError('Datos de comisión no admitidos')
    if contract.status == 'cancelled' or data.get('payer') not in {'tenant', 'owner'}:
        raise APIError('Seleccioná quién paga la comisión de un contrato no anulado')
    if data.get('currency') not in {'ARS', 'USD', 'EUR'}:
        raise APIError('Seleccioná ARS, USD o EUR')
    if db.session.scalar(select(ContractFee.id).where(ContractFee.contract_id == identifier, ContractFee.payer == data['payer'], ContractFee.cancelled_at.is_(None))):
        raise APIError('Ya hay una comisión acordada para esa parte. Revisá la existente antes de crear otra.', 409)
    notes = data.get('notes') or ''
    if not isinstance(notes, str) or len(notes) > 2000:
        raise APIError('Observaciones inválidas (máximo 2000 caracteres)')
    fee = ContractFee(contract_id=identifier, amount=amount(data.get('amount')), currency=data['currency'], payer=data['payer'],
                      agreed_date=day(data.get('agreed_date')), notes=notes, created_by=g.current_user.id)
    db.session.add(fee)
    db.session.flush()
    return public(fee)


@transactional
def pay(identifier, data):
    fee = get_record(ContractFee, identifier, lock=True)
    if set(data) - {'amount', 'payment_date', 'method', 'reference', 'idempotency_key'}:
        raise APIError('Datos de cobro no admitidos')
    key = data.get('idempotency_key')
    if not isinstance(key, str) or not 1 <= len(key) <= 100:
        raise APIError('Identificador de cobro inválido')
    value, paid_on = amount(data.get('amount')), day(data.get('payment_date'))
    method, reference = data.get('method'), data.get('reference') or ''
    if method not in {'transfer', 'cash', 'deposit', 'other'} or not isinstance(reference, str) or len(reference) > 150:
        raise APIError('Medio o referencia inválidos')
    existing = db.session.scalar(select(ContractFeePayment).where(ContractFeePayment.idempotency_key == key))
    if existing:
        if existing.cancelled_at or (existing.fee_id, existing.amount, existing.payment_date, existing.method, existing.reference) != (identifier, value, paid_on, method, reference):
            raise APIError('Ese cobro ya se registró con otros datos o se anuló', 409)
        return public(fee)
    paid = sum((p.amount for p in fee.payments if not p.cancelled_at), ZERO)
    if fee.cancelled_at or value > fee.amount - paid or paid_on < fee.agreed_date:
        raise APIError('Revisá el saldo y la fecha: no se admite cobrar de más ni antes del acuerdo', 409)
    record = ContractFeePayment(fee_id=identifier, amount=value, payment_date=paid_on, method=method,
                               reference=reference, idempotency_key=key, created_by=g.current_user.id)
    fee.payments.append(record)
    db.session.flush()
    return public(fee)


@transactional
def cancel(identifier, data, payment=False):
    if set(data) != {'reason'} or not isinstance(data['reason'], str) or not 1 <= len(data['reason'].strip()) <= 500:
        raise APIError('Indicá el motivo de anulación (hasta 500 caracteres)')
    record = get_record(ContractFeePayment if payment else ContractFee, identifier)
    fee = get_record(ContractFee, record.fee_id if payment else identifier, lock=True)
    if not payment and any(not p.cancelled_at for p in fee.payments):
        raise APIError('Primero anulá los cobros de esta comisión', 409)
    if not record.cancelled_at:
        record.cancelled_at, record.cancellation_reason = utcnow(), data['reason'].strip()
    db.session.flush()
    return public(fee)
