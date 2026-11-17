"""Exact official dates only; unavailable observations never become estimated rates."""
import json
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4

from flask import g
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.extensions import db
from app.models import RentalContract, OfficialIndex, AdjustmentQuote
from app.models.common import utcnow, business_today
from app.services.management_service import APIError, get_record, money, transactional
from app.services.report_service import add_months

IPC_SERIES = '148.3_INIVELNAL_DICI_M_26'
IPC_URL = 'https://apis.datos.gob.ar/series/api/series'
ICL_URL = 'https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/40'


def read_json(url):
    try:
        request = Request(url, headers={'User-Agent': 'Mozilla/5.0 BricksAlquileres/1.0', 'Accept': 'application/json'})
        with urlopen(request, timeout=12) as response:
            final = urlsplit(response.url)
            if final.scheme != 'https' or final.hostname != urlsplit(url).hostname:
                raise ValueError('Redirección inesperada de la fuente oficial')
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError()
        return json.loads(raw, parse_float=Decimal, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except Exception as error:
        raise APIError('No se pudo consultar la fuente oficial. Reintentá; no se aplicó ningún aumento.', 503) from error


def positive(value):
    try:
        if value is None or isinstance(value, bool):
            raise ValueError()
        result = Decimal(str(value))
        if not result.is_finite() or result <= 0 or result >= Decimal('1000000000000'):
            raise ValueError()
        return result.quantize(Decimal('.0000000001'))
    except (ValueError, InvalidOperation):
        raise APIError('La fuente oficial devolvió un índice inválido. No se puede calcular.', 503) from None


def observations(kind, dates):
    """Reuse complete recent persisted data, otherwise validate a full range before upsert."""
    cached = list(db.session.scalars(select(OfficialIndex).where(OfficialIndex.kind == kind, OfficialIndex.value_date.in_(dates))))
    if len(cached) == len(dates) and all(row.fetched_at > utcnow() - timedelta(hours=24) for row in cached):
        return {row.value_date: row.value for row in cached}, cached[0].source_url
    start, end = min(dates), max(dates)
    if kind == 'ICL':
        url = ICL_URL + '?' + urlencode({'desde': start.isoformat(), 'hasta': end.isoformat(), 'limit': 3000})
        payload = read_json(url)
        try:
            groups = payload['results']
            if payload['status'] != 200 or len(groups) != 1 or groups[0]['idVariable'] != 40:
                raise ValueError()
            rows = groups[0]['detalle']
            pairs = [(row['fecha'], row['valor']) for row in rows]
        except (KeyError, TypeError, ValueError, IndexError):
            raise APIError('Formato ICL oficial inesperado. No se puede calcular.', 503) from None
    else:
        url = IPC_URL + '?' + urlencode({'ids': IPC_SERIES, 'start_date': start.isoformat(), 'end_date': end.isoformat(), 'limit': 1000, 'format': 'json'})
        payload = read_json(url)
        try:
            if payload['meta'][1]['field']['id'] != IPC_SERIES:
                raise ValueError()
            pairs = payload['data']
        except (KeyError, TypeError, ValueError, IndexError):
            raise APIError('Formato IPC oficial inesperado. No se puede calcular.', 503) from None
    values = {}
    try:
        for raw_date, raw_value in pairs:
            day = date.fromisoformat(raw_date)
            if day in dates:
                if day in values:
                    raise ValueError()
                values[day] = positive(raw_value)
    except (ValueError, TypeError):
        raise APIError('Fechas oficiales inválidas o duplicadas. No se puede calcular.', 503) from None
    missing = sorted(set(dates) - set(values))
    if missing:
        dates_label = ', '.join(day.strftime('%d/%m/%Y') for day in missing)
        reason = 'La fecha del aumento es futura y el índice todavía no está disponible.' if any(day > business_today() for day in missing) else 'La fuente oficial todavía no tiene todos los índices necesarios.'
        raise APIError(f'{reason} Falta {kind} para: {dates_label}. Volvé a consultar cuando se publique. No se aplicó ningún aumento.', 409)
    insert = pg_insert if db.engine.dialect.name == 'postgresql' else sqlite_insert
    now = utcnow()
    for day, value in values.items():
        statement = insert(OfficialIndex).values(kind=kind, value_date=day, value=value, source_url=url, fetched_at=now)
        db.session.execute(statement.on_conflict_do_update(index_elements=['kind', 'value_date'], set_={'value': value, 'source_url': url, 'fetched_at': now}))
    return values, url


@transactional
def preview(identifier, data):
    from app.services.rental_workspace_service import rent_on
    if set(data) - {'kind', 'start', 'end', 'effective_date', 'billing_treatment'} or not {'kind', 'start', 'end', 'effective_date'} <= set(data):
        raise APIError('Indicá índice, período inicial/final y fecha de aplicación')
    contract = get_record(RentalContract, identifier)
    kind = data['kind']
    try:
        start = date.fromisoformat(data['start'])
        end = date.fromisoformat(data['end'])
        effective = date.fromisoformat(data['effective_date'])
    except (TypeError, ValueError):
        raise APIError('Fechas inválidas') from None
    if not isinstance(kind, str) or kind not in {'IPC', 'ICL'} or contract.status != 'active':
        raise APIError('Solo se puede consultar IPC/ICL para un contrato activo')
    previous = max((a.effective_date for a in contract.adjustments if a.effective_date < effective), default=contract.start_date)
    from app.services.rental_schedule_service import validate_adjustment
    treatment = validate_adjustment(contract, effective, data.get('billing_treatment'))
    if start < previous.replace(day=1) or start > end or end > effective or (end.year - start.year) * 12 + end.month - start.month > 36:
        raise APIError('Revisá el período: desde la última actualización, hasta la aplicación y máximo 36 meses')
    if kind == 'IPC':
        if start.day != 1 or end.day != 1 or end >= effective.replace(day=1):
            raise APIError('IPC requiere meses completos anteriores al mes de aplicación')
        denominator = add_months(start, -1)
        dates = []
        day = denominator
        while day <= end:
            dates.append(day)
            day = add_months(day, 1)
        values, url = observations(kind, dates)
        factor = values[end] / values[denominator]
        rates = [{'month': day.isoformat(), 'percentage': str((values[day] / values[add_months(day, -1)] - 1) * 100)} for day in dates[1:]]
    else:
        if start != previous or end != effective:
            raise APIError('ICL debe comparar la fecha de inicio/último ajuste con la fecha de aplicación')
        dates = sorted({start, end})
        values, url = observations(kind, dates)
        factor = values[end] / values[start]
        rates = []
    base = rent_on(contract, effective)
    amount = money(base * factor)
    if base <= 0 or amount < base or amount >= Decimal('10000000000'):
        raise APIError('El resultado no puede aplicarse con este formulario; revisá el contrato y el período', 409)
    detail = {'kind': kind, 'start': start.isoformat(), 'end': end.isoformat(), 'source_url': url,
              'factor': str(factor), 'percentage': str(((factor - 1) * 100).quantize(Decimal('.0001'))),
              'observations': [{'date': day.isoformat(), 'value': str(values[day])} for day in sorted(values)],
              'monthly_rates': rates, 'base': str(base), 'new_amount': str(amount), 'consulted_at': now_iso()}
    return store_preview(contract, effective, base, amount, detail, treatment)


def store_preview(contract, effective, base, amount, detail, treatment):
    from app.services.rental_schedule_service import preview_billing
    if amount < 0 or amount >= Decimal('10000000000'):
        raise APIError('El importe calculado está fuera del rango admitido; revisá el contrato y los valores.')
    detail['billing_treatment'] = treatment
    detail['billing_cycle'] = contract.billing_cycle
    detail['billing'] = preview_billing(contract, effective, amount, treatment)
    quote = AdjustmentQuote(id=uuid4().hex, contract_id=contract.id, created_by=g.current_user.id, effective_date=effective,
                            base_amount=base, detail=detail, expires_at=utcnow() + timedelta(minutes=30))
    db.session.add(quote)
    return {'quote_id': quote.id, 'effective_date': effective.isoformat(), 'currency': contract.currency,
            'index_base_date': max((a.effective_date for a in contract.adjustments if a.effective_date < effective), default=contract.start_date).isoformat(), **detail}


@transactional
def manual_preview(identifier, data):
    from app.services.rental_workspace_service import manual_adjustment_values
    from app.services.rental_schedule_service import validate_adjustment, rent_on
    contract = get_record(RentalContract, identifier)
    try:
        effective = date.fromisoformat(data.get('effective_date', ''))
    except (TypeError, ValueError):
        raise APIError('Ingresá una fecha válida de aplicación') from None
    treatment = validate_adjustment(contract, effective, data.get('billing_treatment'))
    base = rent_on(contract, effective)
    amount, factor, detail, mode, source = manual_adjustment_values(contract, base, data)
    detail.update(kind=mode, source_url=source, base=str(base), new_amount=str(amount), factor=str(factor),
                  percentage=str(((factor - 1) * 100).quantize(Decimal('.0001'))), observations=[], consulted_at=now_iso())
    return store_preview(contract, effective, base, amount, detail, treatment)


def now_iso():
    return utcnow().isoformat() + 'Z'


def confirmed_quote(identifier, quote_id, effective, base):
    if not isinstance(quote_id, str) or len(quote_id) != 32:
        raise APIError('Consultá los índices antes de confirmar')
    quote = db.session.scalar(select(AdjustmentQuote).where(AdjustmentQuote.id == quote_id).with_for_update())
    if quote is None or quote.contract_id != identifier or quote.created_by != g.current_user.id or quote.used_at or quote.expires_at < utcnow():
        raise APIError('La consulta venció o ya se usó. Volvé a consultar los índices.', 409)
    contract = get_record(RentalContract, identifier)
    if quote.effective_date != effective or quote.base_amount != base or quote.detail.get('billing_cycle', 'calendar') != contract.billing_cycle:
        raise APIError('Cambió el contrato o la fecha. Volvé a consultar los índices.', 409)
    quote.used_at = utcnow()
    return quote.detail
