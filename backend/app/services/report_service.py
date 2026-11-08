import calendar
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import RentalContract, RentAdjustment, RentCharge, RentPayment, OwnerSettlement, Expense, Person, Property, RentalContractTenant
from app.models.common import business_today, ZERO
from app.services.management_service import APIError, get_record, serialize


def integer(value, name, minimum, maximum):
    try:
        if isinstance(value, bool):
            raise ValueError()
        result = int(value)
        if not minimum <= result <= maximum:
            raise ValueError()
        return result
    except (ValueError, TypeError):
        raise APIError(f"{name} inválido") from None


def period_arguments(arguments):
    year = integer(arguments.get("year"), "year", 1, 9998)
    month = integer(arguments.get("month"), "month", 1, 12)
    currency = arguments.get("currency", "ARS")
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isascii() or not currency.isalpha() or currency != currency.upper():
        raise APIError("currency inválida")
    return year, month, currency


def balances_by_currency(records):
    totals = {}
    for record in records:
        totals[record.currency] = totals.get(record.currency, ZERO) + record.outstanding_balance
    return {currency: str(amount) for currency, amount in totals.items()}


def add_months(day, months):
    index = day.year * 12 + day.month - 1 + months
    year, month = divmod(index, 12)
    if year > 9999:
        return None
    return date(year, month + 1, min(day.day, calendar.monthrange(year, month + 1)[1]))


class ReportService:
    @staticmethod
    def tenant_debts(identifier):
        get_record(Person, identifier)
        charges = list(db.session.scalars(select(RentCharge).join(RentalContract).where(
            or_(RentalContract.tenant_id == identifier,
                RentalContract.tenant_links.any(RentalContractTenant.person_id == identifier)),
            RentCharge.cancelled_at.is_(None))))
        pending = [charge for charge in charges if charge.outstanding_balance > 0]
        overdue = [charge for charge in pending if charge.due_date < business_today()]
        return {"tenant_id": identifier, "balances_by_currency": balances_by_currency(pending),
                "overdue_by_currency": balances_by_currency(overdue), "charges": [serialize(c) for c in pending]}

    @staticmethod
    def owner_balances(identifier):
        get_record(Person, identifier)
        settlements = list(db.session.scalars(select(OwnerSettlement).where(OwnerSettlement.owner_id == identifier).order_by(OwnerSettlement.id)))
        return {"owner_id": identifier, "balances_by_currency": balances_by_currency(settlements),
                "settlements": [serialize(s) for s in settlements]}

    @staticmethod
    def dashboard(arguments):
        year, month, currency = period_arguments(arguments)
        detail = arguments.get('detail')
        if detail and detail not in {'collections', 'pending', 'administration_fees', 'expenses'}:
            raise APIError('Indicador inválido')
        start = date(year, month, 1)
        end = add_months(start, 1)
        payments = list(db.session.scalars(select(RentPayment).join(RentCharge, RentPayment.charge_id == RentCharge.id).where(
            RentPayment.payment_date >= start, RentPayment.payment_date < end,
            RentPayment.cancelled_at.is_(None), RentCharge.currency == currency)))
        charges = list(db.session.scalars(select(RentCharge).options(selectinload(RentCharge.payments)).where(RentCharge.period_year == year,
            RentCharge.period_month == month, RentCharge.currency == currency, RentCharge.cancelled_at.is_(None))))
        settlements = list(db.session.scalars(select(OwnerSettlement).options(selectinload(OwnerSettlement.transfers)).where(OwnerSettlement.period_year == year,
            OwnerSettlement.period_month == month, OwnerSettlement.currency == currency, OwnerSettlement.cancelled_at.is_(None))))
        expenses = list(db.session.scalars(select(Expense).where(Expense.expense_date >= start,
            Expense.expense_date < end, Expense.currency == currency)))
        result = {"year": year, "month": month, "currency": currency,
                "collections": str(sum((p.amount for p in payments), ZERO)),
                "pending": str(sum((c.outstanding_balance for c in charges), ZERO)),
                "administration_fees": str(sum((s.administration_fee for s in settlements), ZERO)),
                "expenses": str(sum((e.amount for e in expenses), ZERO)),
                "pending_owner_transfers": str(sum((s.outstanding_balance for s in settlements), ZERO))}
        if detail:
            records = {'collections': payments, 'pending': charges,
                       'administration_fees': settlements, 'expenses': expenses}[detail]
            if detail == 'pending':
                records = [r for r in records if r.outstanding_balance > ZERO]
            contract_ids = {r.contract_id for r in records if hasattr(r, 'contract_id') and r.contract_id}
            if detail == 'administration_fees':
                contract_ids.update(c.contract_id for c in charges)
            contracts = {r.id: r for r in db.session.scalars(select(RentalContract).where(RentalContract.id.in_(contract_ids)))} if contract_ids else {}
            settlement_contracts = {}
            if detail == 'administration_fees':
                # Use the contracts charged in this settlement period, including
                # historical contracts; never guess from the currently active one.
                for charge in charges:
                    contract = contracts[charge.contract_id]
                    settlement_contracts.setdefault(contract.property_id, set()).add(contract.id)
            property_ids = {r.property_id for r in contracts.values()} | {r.property_id for r in records if hasattr(r, 'property_id') and r.property_id}
            properties = {r.id: r for r in db.session.scalars(select(Property).where(Property.id.in_(property_ids)))} if property_ids else {}
            person_ids = {r.tenant_id for r in contracts.values()} | {r.owner_id for r in records if hasattr(r, 'owner_id')}
            people = {r.id: f'{r.first_name} {r.last_name}' for r in db.session.scalars(select(Person).where(Person.id.in_(person_ids)))} if person_ids else {}
            rows = []
            for record in records:
                contract = contracts.get(getattr(record, 'contract_id', None))
                prop = properties.get(contract.property_id if contract else getattr(record, 'property_id', None))
                label = ' '.join(filter(None, [prop.address, prop.unit])) if prop else 'Gasto del negocio'
                person = people.get(record.owner_id if detail == 'administration_fees' else contract.tenant_id if contract else None, '')
                if detail == 'collections':
                    amount, day = record.amount, record.payment_date
                    note = f'{record.payment_method or "Pago"} · {record.reference or "Sin referencia"}'
                elif detail == 'pending':
                    amount, day = record.outstanding_balance, record.due_date
                    note = f'Alquiler: {record.total_amount} {currency} · Cobrado: {record.paid_amount} {currency}'
                elif detail == 'administration_fees':
                    amount, day = record.administration_fee, record.settlement_date
                    note = f'Liquidación #{record.id} · Bruto: {record.gross_amount} {currency}'
                else:
                    amount, day = record.amount, record.expense_date
                    label = record.description or record.category
                    note = f'{record.category} · ' + {'agency': 'Inmobiliaria', 'owner': 'Propietario', 'tenant': 'Inquilino'}.get(record.responsible_party, '')
                    if prop:
                        note += f' · {prop.address}'
                related_contracts = sorted(settlement_contracts.get(record.property_id, set())) if detail == 'administration_fees' else [contract.id] if contract else []
                href = f'/contratos/{related_contracts[0]}' if len(related_contracts) == 1 else f'/propietarios/{record.owner_id}' if detail == 'administration_fees' else None
                if detail == 'expenses':
                    href = f'/gastos?ficha={record.id}&period={year:04}-{month:02}&currency={currency}'
                rows.append({'id': record.id, 'label': label, 'person': person, 'date': day.isoformat(), 'amount': str(amount), 'note': note,
                             'href': href, 'contract_ids': related_contracts,
                             'person_href': f'/propietarios/{record.owner_id}' if detail == 'administration_fees' else f'/inquilinos/{contract.tenant_id}' if contract else None})
            result['rows'] = sorted(rows, key=lambda row: (row['date'], row['id']), reverse=True)
        return result

    @staticmethod
    def upcoming(kind, arguments):
        days = integer(arguments.get("days", 30), "days", 0, 3660)
        today = business_today()
        until = today + timedelta(days=days)
        contracts = list(db.session.scalars(select(RentalContract).where(RentalContract.status == "active")))
        if kind == "expirations":
            return [serialize(c) for c in sorted(contracts, key=lambda c: c.end_date) if today <= c.end_date <= until]
        results = []
        for contract in contracts:
            adjustments = list(db.session.scalars(select(RentAdjustment).where(RentAdjustment.contract_id == contract.id).order_by(RentAdjustment.effective_date)))
            future = [a.effective_date for a in adjustments if today <= a.effective_date <= contract.end_date]
            next_date = min(future) if future else None
            frequency = contract.adjustment_frequency_months
            if not next_date and frequency:
                base = max((a.effective_date for a in adjustments if a.effective_date < today), default=contract.start_date)
                months_elapsed = max(0, (today.year - base.year) * 12 + today.month - base.month)
                steps = max(1, months_elapsed // frequency)
                next_date = add_months(base, steps * frequency)
                if next_date and next_date < today:
                    next_date = add_months(base, (steps + 1) * frequency)
            if next_date and today <= next_date <= until and next_date <= contract.end_date:
                results.append({"contract_id": contract.id, "property_id": contract.property_id,
                                "tenant_id": contract.tenant_id, "tenant_ids": contract.tenant_ids, "next_adjustment_date": next_date.isoformat(),
                                "adjustment_index": contract.adjustment_index})
        return sorted(results, key=lambda result: result["next_adjustment_date"])
