"""Service obligations are instructions, never inferred debts or ledger entries."""
import calendar
import re
from decimal import Decimal, InvalidOperation
from datetime import date
from sqlalchemy import select
from app.extensions import db
from app.models import Property, RentalContract, Reminder
from app.services.management_service import APIError, get_record, transactional
from app.services.report_service import integer

SERVICES = {'electricity': 'Luz / EPEC', 'water': 'Agua', 'gas': 'Gas', 'municipal': 'Municipal', 'provincial': 'Rentas / DGR', 'expenses_regular': 'Expensas ordinarias', 'expenses_extra': 'Expensas extraordinarias', 'internet': 'Internet', 'insurance': 'Seguro', 'other': 'Otro'}
PAYERS = {'undefined', 'tenant', 'owner', 'shared'}
METHODS = {'undefined', 'direct', 'collect_pay', 'pay_deduct'}


def validate_rules(value):
    if not isinstance(value, list) or len(value) > 40:
        raise APIError('Configuración de servicios inválida')
    result, seen = [], set()
    for item in value:
        if not isinstance(item, dict) or set(item) - {'service', 'name', 'reference_amount', 'payer', 'management', 'frequency', 'reference', 'notes', 'day'}:
            raise APIError('Datos de servicio inválidos')
        service = item.get('service')
        if not isinstance(service, str) or (service not in SERVICES and not re.fullmatch(r'custom:[a-f0-9]{32}', service)) or service in seen:
            raise APIError('Servicio inválido o repetido')
        seen.add(service)
        name = item.get('name') or ''
        if not isinstance(name, str) or len(name) > 100 or service.startswith('custom:') and not name.strip():
            raise APIError('Escribí el nombre del concepto personalizado (hasta 100 caracteres)')
        amount = item.get('reference_amount')
        if amount is not None:
            try:
                amount = Decimal(str(amount))
                if isinstance(item['reference_amount'], bool) or not amount.is_finite() or amount < 0 or amount >= 10**10 or amount != amount.quantize(Decimal('.01')):
                    raise ValueError()
            except (ValueError, InvalidOperation):
                raise APIError('Importe de referencia inválido') from None
        rule = {'service': service, 'payer': item.get('payer', 'undefined'), 'management': item.get('management', 'undefined'), 'frequency': item.get('frequency', 'occasional')}
        if rule['payer'] not in PAYERS or rule['management'] not in METHODS or rule['frequency'] not in {'monthly', 'other', 'occasional'}:
            raise APIError('Responsable, gestión o frecuencia inválidos')
        if rule['management'] == 'collect_pay' and rule['payer'] != 'tenant' or rule['management'] == 'pay_deduct' and rule['payer'] != 'owner':
            raise APIError('La gestión seleccionada no coincide con quién está a cargo')
        day = item.get('day')
        if day is not None and (type(day) is not int or not 1 <= day <= 31):
            raise APIError('Día de control inválido')
        rule['day'] = day
        rule['name'] = name.strip()
        rule['reference_amount'] = str(amount) if amount is not None else None
        for key, limit in [('reference', 150), ('notes', 1000)]:
            text = item.get(key) or ''
            if not isinstance(text, str) or len(text) > limit:
                raise APIError('Referencia u observaciones inválidas')
            rule[key] = text.strip()
        result.append(rule)
    return result


@transactional
def generate_controls(contract_id, data):
    if not isinstance(data, dict) or set(data) != {'year', 'month'}:
        raise APIError('Indicá año y mes')
    year, month = integer(data['year'], 'year', 1, 9998), integer(data['month'], 'month', 1, 12)
    contract = get_record(RentalContract, contract_id)
    get_record(Property, contract.property_id, lock=True)
    contract = get_record(RentalContract, contract_id, lock=True)
    first, last = date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    if contract.status != 'active' or first > contract.end_date or last < contract.start_date:
        raise APIError('El período no corresponde a un contrato activo')
    created, existing = 0, 0
    methods = {'direct': 'Solicitar o verificar comprobante de pago directo.', 'collect_pay': 'Confirmar importe, cobrar al inquilino y realizar el pago.', 'pay_deduct': 'Confirmar importe, realizar el pago y registrar el descuento al propietario.', 'undefined': 'Definir quién realiza el pago y cómo se gestiona.'}
    for rule in validate_rules(contract.utility_rules or []):
        if rule['frequency'] != 'monthly':
            continue
        key = f'utility:{contract.id}:{rule["service"]}:{year:04}-{month:02}'
        if db.session.scalar(select(Reminder.id).where(Reminder.source_key == key)):
            existing += 1
            continue
        due = min(max(date(year, month, min(rule['day'] or contract.payment_day or 10, last.day)), contract.start_date), contract.end_date)
        label = rule.get('name') or SERVICES.get(rule['service'], 'Otro')
        action = {'direct': 'Verificar pago de', 'collect_pay': 'Cobrar y pagar', 'pay_deduct': 'Pagar', 'undefined': 'Revisar pago de'}[rule['management']]
        reminder = Reminder(property_id=contract.property_id, contract_id=contract.id, title=f'{action} {label} · {month:02}/{year}', description=f'Control mensual. A cargo: { {"tenant":"inquilino","owner":"propietario","shared":"compartido","undefined":"por definir"}[rule["payer"]] }. {rule["notes"]}', due_date=due, category='Servicio / control', priority='normal', progress='pending', status='pending', amount=None, next_action=methods[rule['management']], source_key=key, responsible_person_id=contract.tenant_id if rule['payer']=='tenant' else None)
        db.session.add(reminder)
        created += 1
    db.session.flush()
    return {'created': created, 'existing': existing}
