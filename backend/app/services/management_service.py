import calendar
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from functools import wraps

from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import (Person, Property, PropertyOwner, RentalContract, RentAdjustment,
                        RentCharge, RentPayment, OwnerSettlement, OwnerTransfer,
                        Expense, Document, Reminder, RentalContractTenant, SaleOperation, ContractGuarantor)
from app.models.common import business_today, ZERO, utcnow
from app.repositories.management_repository import ManagementRepository as Repository


class APIError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def transactional(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            result = function(*args, **kwargs)
            db.session.commit()
            return result
        except IntegrityError:
            db.session.rollback()
            raise APIError("La operación viola una restricción: duplicado, referencia o importe inválido", 409) from None
        except Exception:
            db.session.rollback()
            raise
    return wrapped


RESOURCES = {
    "persons": Person, "properties": Property, "property-owners": PropertyOwner,
    "contracts": RentalContract, "adjustments": RentAdjustment, "expenses": Expense,
    "documents": Document, "reminders": Reminder, "charges": RentCharge,
    "payments": RentPayment, "settlements": OwnerSettlement, "transfers": OwnerTransfer,
    "contract-tenants": RentalContractTenant, "sales": SaleOperation,
}
FINANCIAL = {RentCharge, RentPayment, OwnerSettlement, OwnerTransfer}
DEFAULTS = {
    Property: {"status": "available"}, PropertyOwner: {"ownership_percentage": Decimal("100.00")},
    RentalContract: {"currency": "ARS", "status": "active"},
    SaleOperation: {"currency": "ARS", "commission": ZERO, "status": "pending"},
    Expense: {"currency": "ARS"}, Reminder: {"status": "pending"},
    RentCharge: {"other_charges": ZERO, "discounts": ZERO, "status": "pending"},
    OwnerSettlement: {"deductions": ZERO, "currency": "ARS", "status": "pending"},
}
READONLY = {"id", "created_at", "uploaded_at", "completed_at", "cancelled_at", "cancellation_reason", "confirmed_at", "source_key"}
ENUMS = {
    (Property, "operation_type"): {"alquiler", "venta"},
    (Property, "status"): {"available", "rented", "sold", "inactive"},
    (RentalContract, "status"): {"active", "expired", "terminated", "cancelled"},
    (SaleOperation, "status"): {"pending", "completed", "cancelled"},
    (Reminder, "status"): {"pending", "completed", "cancelled"},
    (Expense, "responsible_party"): {"owner", "tenant", "agency"},
}
FOREIGN_MODELS = {"properties": Property, "persons": Person, "rental_contracts": RentalContract,
                  "rent_charges": RentCharge, "owner_settlements": OwnerSettlement, "rent_payments": RentPayment, "owner_transfers": OwnerTransfer}


def money(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def serialize(record):
    result = {}
    for column in inspect(type(record)).columns:
        if column.name == "password_hash":
            continue
        value = getattr(record, column.name)
        if isinstance(value, Decimal):
            value = str(value)
        elif isinstance(value, (date, datetime)):
            value = value.isoformat()
        result[column.name] = value
    if isinstance(record, RentalContract):
        result["tenant_ids"] = record.tenant_ids
        result["guarantor_ids"] = record.guarantor_ids
    if isinstance(record, Property):
        result["ownerships"] = [{"person_id": link.person_id, "ownership_percentage": str(link.ownership_percentage)} for link in record.owners]
    if isinstance(record, RentCharge):
        result.update(paid_amount=str(record.paid_amount), outstanding_balance=str(record.outstanding_balance), status=record.calculated_status)
    if isinstance(record, OwnerSettlement):
        result.update(transferred_amount=str(record.transferred_amount), outstanding_balance=str(record.outstanding_balance), status=record.calculated_status)
    return result


def get_record(model, identifier, lock=False):
    record = Repository.get(model, identifier, lock)
    if record is None:
        raise APIError("Registro no encontrado", 404)
    return record


def convert(column, value):
    if value is None:
        if not column.nullable:
            raise APIError(f"{column.name} es obligatorio")
        return None
    if column.name == "utility_rules":
        from app.services.utility_service import validate_rules
        return validate_rules(value)
    kind = column.type.python_type
    try:
        if kind is Decimal:
            if isinstance(value, bool):
                raise ValueError()
            converted = Decimal(str(value))
            if not converted.is_finite() or converted < 0:
                raise ValueError()
            scale = column.type.scale
            if converted != converted.quantize(Decimal(1).scaleb(-scale)):
                raise ValueError()
            if converted >= Decimal(10) ** (column.type.precision - scale):
                raise ValueError()
            return converted
        if kind is int:
            if isinstance(value, bool) or not isinstance(value, (int, str)):
                raise ValueError()
            return int(value)
        if kind is date:
            return date.fromisoformat(value)
        if kind is str:
            if not isinstance(value, str) or not value.strip():
                raise ValueError()
            value = value.strip()
            if getattr(column.type, "length", None) and len(value) > column.type.length:
                raise ValueError()
            return value
    except (ValueError, TypeError, InvalidOperation, OverflowError):
        raise APIError(f"Valor inválido para {column.name}") from None
    raise APIError(f"Campo no admitido: {column.name}")


def payload(model, data, extra_readonly=()):
    if not isinstance(data, dict):
        raise APIError("Se requiere un objeto JSON")
    columns = {c.name: c for c in inspect(model).columns}
    blocked = READONLY | set(extra_readonly)
    for key in data:
        if key not in columns or key in blocked:
            raise APIError(f"Campo no admitido: {key}")
    return {key: convert(columns[key], value) for key, value in data.items()}


def validate(record, creating=False, check_overlap=True):
    model = type(record)
    for column in inspect(model).columns:
        value = getattr(record, column.name)
        if value is None and not column.nullable and not column.primary_key and column.default is None:
            raise APIError(f"{column.name} es obligatorio")
        if value is not None:
            if column.type.python_type is Decimal:
                convert(column, value)
            for foreign_key in column.foreign_keys:
                # Composite payment FK also references charge.contract_id; it is
                # not a charge primary key. The service and DB check that pair.
                if foreign_key.column.name == "id":
                    foreign_model = FOREIGN_MODELS[foreign_key.column.table.name]
                    get_record(foreign_model, value)
    for (enum_model, field), options in ENUMS.items():
        if enum_model is model and getattr(record, field) not in options:
            raise APIError(f"Valor inválido para {field}; valores: {', '.join(sorted(options))}")
    if hasattr(record, "currency"):
        currency = record.currency
        if not currency or len(currency) != 3 or not currency.isascii() or not currency.isalpha() or currency != currency.upper():
            raise APIError("currency debe ser un código de tres letras mayúsculas")
    if isinstance(record, Property):
        for field in ("rooms", "bedrooms", "bathrooms", "total_area", "covered_area"):
            if getattr(record, field) is not None and getattr(record, field) < 0:
                raise APIError(f"{field} no puede ser negativo")
        if record.agency_ownership_percentage is not None and not 0 <= record.agency_ownership_percentage <= 100:
            raise APIError("La participación propia debe estar entre 0 y 100")
    if isinstance(record, Person) and record.cbu:
        import re
        if not re.fullmatch(r"\d{22}",record.cbu):
            raise APIError("El CBU debe tener 22 dígitos, sin espacios")
    if isinstance(record, RentalContract):
        if record.collection_cbu:
            import re
            if not re.fullmatch(r"\d{22}",record.collection_cbu):
                raise APIError("El CBU de cobro debe tener 22 dígitos, sin espacios")
        if record.payment_day is not None and not 1 <= record.payment_day <= 31:
            raise APIError("El día de pago debe estar entre 1 y 31")
        if record.next_adjustment_date and not record.start_date <= record.next_adjustment_date <= record.end_date:
            raise APIError("El próximo ajuste debe estar dentro del contrato")
        if record.end_date <= record.start_date:
            raise APIError("end_date debe ser posterior a start_date")
        if record.administration_percentage is not None and record.administration_percentage > 100:
            raise APIError("administration_percentage debe estar entre 0 y 100")
        if record.adjustment_frequency_months is not None and record.adjustment_frequency_months <= 0:
            raise APIError("adjustment_frequency_months debe ser positivo")
        if check_overlap:
            from app.services.contract_service import ContractService
            ContractService.validate_overlap(record)
    if isinstance(record, PropertyOwner):
        get_record(Property, record.property_id, lock=True)
        if record.ownership_percentage > 100:
            raise APIError("ownership_percentage debe estar entre 0 y 100")
        with db.session.no_autoflush:
            owners = Repository.list(PropertyOwner, {"property_id": record.property_id})
            total = sum((o.ownership_percentage for o in owners if o.id != record.id), ZERO)
        if total + record.ownership_percentage > 100:
            raise APIError("La suma de porcentajes de propietarios supera 100")
    if isinstance(record, RentalContractTenant):
        contract = get_record(RentalContract, record.contract_id)
        get_record(Property, contract.property_id, lock=True)
        from app.services.contract_service import ContractService
        ContractService.validate_link(record)
    if isinstance(record, SaleOperation):
        if not record.property_id and not record.operation_description:
            raise APIError("Indicá una propiedad o una descripción de la operación")
        if (record.personal_commission or ZERO) + (record.agency_commission or ZERO) > record.commission:
            raise APIError("Las comisiones distribuidas no pueden superar la comisión total")
        if record.buyer_id is not None and record.buyer_id == record.seller_id:
            raise APIError("El comprador y el vendedor deben ser personas distintas")
        if record.commission > record.price:
            raise APIError("La comisión no puede superar el precio de venta")
        if record.status == "completed" and record.sale_date > business_today():
            raise APIError("Una compraventa completada no puede tener fecha futura")
    if isinstance(record, RentAdjustment):
        contract = get_record(RentalContract, record.contract_id)
        if not contract.start_date <= record.effective_date <= contract.end_date:
            raise APIError("El ajuste debe estar dentro de las fechas del contrato")
    if isinstance(record, (Expense, Document, Reminder)) and record.property_id and record.contract_id:
        contract = get_record(RentalContract, record.contract_id)
        if contract.property_id != record.property_id:
            raise APIError("El contrato no corresponde a la propiedad")
    if isinstance(record, Document):
        if (record.period_year is None) != (record.period_month is None):
            raise APIError("Indicá año y mes del comprobante")
        if record.period_year is not None and (not 1 <= record.period_year <= 9999 or not 1 <= record.period_month <= 12):
            raise APIError("Período del comprobante inválido")
        for field, related_model in (("charge_id", RentCharge), ("payment_id", RentPayment), ("settlement_id", OwnerSettlement), ("transfer_id", OwnerTransfer)):
            identifier = getattr(record, field)
            if identifier:
                related = get_record(related_model, identifier)
                related_contract = related.contract_id if hasattr(related, "contract_id") else None
                if record.contract_id and related_contract and record.contract_id != related_contract:
                    raise APIError("El comprobante no corresponde al contrato indicado")
                related_property = related.property_id if hasattr(related, "property_id") else related.settlement.property_id if isinstance(related, OwnerTransfer) else related.contract.property_id
                if record.property_id and record.property_id != related_property:
                    raise APIError("El comprobante no corresponde a la propiedad indicada")
        import re
        if not (re.fullmatch(r'[a-f0-9]{32}\.(pdf|png|jpg)', record.file_path) or record.file_path.startswith('https://')):
            raise APIError("Adjuntá un archivo o ingresá un enlace HTTPS válido")
    if isinstance(record, Reminder):
        if record.responsible_person_id:
            get_record(Person, record.responsible_person_id)
        if record.priority and record.priority not in {"normal", "urgent"}:
            raise APIError("Prioridad inválida")
        if record.progress and record.progress not in {"pending", "in_progress", "recurring"}:
            raise APIError("Seguimiento inválido")
        record.completed_at = (record.completed_at or utcnow()) if record.status == "completed" else None


def filters_for(model, arguments):
    allowed = {"property_id", "contract_id", "person_id", "owner_id", "tenant_id", "charge_id", "settlement_id", "period_year", "period_month", "status", "currency", "buyer_id", "seller_id"}
    columns = {c.name: c for c in inspect(model).columns}
    filters = {}
    for key, value in arguments.items():
        if key not in allowed or key not in columns:
            raise APIError(f"Filtro no admitido: {key}")
        filters[key] = convert(columns[key], value)
    return filters


def lock_parent_properties(record, values):
    # Same lock order as payments: property, contract, dependent record.
    if isinstance(record, (RentalContract, PropertyOwner, SaleOperation)):
        for identifier in sorted(v for v in {record.property_id, values.get("property_id", record.property_id)} if v is not None):
            get_record(Property, identifier, lock=True)
    elif isinstance(record, RentalContractTenant):
        contract = get_record(RentalContract, record.contract_id)
        get_record(Property, contract.property_id, lock=True)
        get_record(RentalContract, contract.id, lock=True)


def extract_guarantors(data):
    if not isinstance(data, dict):
        raise APIError("Se requiere un objeto JSON")
    values = dict(data)
    identifiers = values.pop("guarantor_ids", None)
    if identifiers is not None:
        if not isinstance(identifiers, list) or len(identifiers) > 20:
            raise APIError("La lista de garantes no es válida")
        identifiers = [convert(Person.__table__.c.id, value) for value in identifiers]
        if any(value is None or value <= 0 for value in identifiers) or len(set(identifiers)) != len(identifiers):
            raise APIError("Garantes inválidos o duplicados")
        for identifier in identifiers:
            get_record(Person, identifier)
    return values, identifiers


def sync_guarantors(contract, identifiers):
    if identifiers is None:
        return
    if set(identifiers) & set(contract.tenant_ids):
        raise APIError("Un inquilino no puede ser garante del mismo contrato")
    if contract.charges and set(identifiers) != set(contract.guarantor_ids):
        raise APIError("Con mensualidades registradas se conserva la garantía del contrato", 409)
    existing = {link.person_id: link for link in contract.guarantor_links}
    for identifier, link in existing.items():
        if identifier not in identifiers:
            db.session.delete(link)
    for identifier in set(identifiers) - existing.keys():
        db.session.add(ContractGuarantor(contract=contract, person_id=identifier))
    db.session.flush()
    db.session.expire(contract, ["guarantor_links"])


def extract_ownerships(data):
    if not isinstance(data, dict):
        raise APIError("Se requiere un objeto JSON")
    values = dict(data)
    owners = values.pop("ownerships", None)
    if owners is not None:
        if not isinstance(owners, list) or len(owners) > 30:
            raise APIError("Lista de propietarios inválida")
        seen, total = set(), ZERO
        for owner in owners:
            if not isinstance(owner, dict) or set(owner) != {"person_id", "ownership_percentage"}:
                raise APIError("Completá persona y porcentaje para cada propietario")
            identifier = convert(Person.__table__.c.id, owner["person_id"])
            percentage = convert(PropertyOwner.__table__.c.ownership_percentage, owner["ownership_percentage"])
            if not identifier or identifier in seen or percentage is None or percentage <= 0:
                raise APIError("Propietario duplicado o participación inválida")
            get_record(Person, identifier)
            seen.add(identifier)
            total += percentage
        if total > 100:
            raise APIError("La suma de participaciones no puede superar el 100%")
    return values, owners


def sync_ownerships(record, owners):
    if owners is None:
        return
    for link in list(record.owners):
        db.session.delete(link)
    db.session.flush()
    for owner in owners:
        db.session.add(PropertyOwner(property_id=record.id, person_id=int(owner["person_id"]), ownership_percentage=Decimal(str(owner["ownership_percentage"]))))
    db.session.flush()
    db.session.expire(record, ["owners"])


class ManagementService:
    @staticmethod
    def list(resource, arguments=None):
        model = RESOURCES[resource]
        filters = filters_for(model, arguments or {})
        status = filters.pop("status", None) if model in {RentCharge, OwnerSettlement} else None
        if model is RentalContract and "tenant_id" in filters:
            from app.repositories.contract_repository import ContractRepository
            records = ContractRepository.for_tenant(filters.pop("tenant_id"), filters)
        else:
            records = Repository.list(model, filters)
        return [r for r in records if status is None or r.calculated_status == status]

    @staticmethod
    @transactional
    def create(resource, data):
        model = RESOURCES[resource]
        if model in FINANCIAL:
            return FinanceService.create(resource, data)
        ownerships = None
        if model is Property:
            data, ownerships = extract_ownerships(data)
            data = {"price": "0", "operation_type": "alquiler", **data}
            data.setdefault("title", data.get("address"))
        tenant_ids = None
        guarantor_ids = None
        if model is RentalContract:
            from app.services.contract_service import ContractService
            data, guarantor_ids = extract_guarantors(data)
            data, tenant_ids = ContractService.extract_tenants(data)
        values = {**DEFAULTS.get(model, {}), **payload(model, data)}
        record = model(**values)
        validate(record, creating=True)
        Repository.add(record)
        if model is Property:
            sync_ownerships(record, ownerships)
        if model is RentalContract:
            ContractService.sync_tenants(record, tenant_ids)
            sync_guarantors(record, guarantor_ids)
        return record

    @staticmethod
    @transactional
    def update(resource, identifier, data):
        model = RESOURCES[resource]
        if model in FINANCIAL:
            raise APIError("Las operaciones financieras son inmutables; utilice anulación", 409)
        if model is RentalContractTenant:
            raise APIError("Para cambiar una asociación, elimínela y agregue la nueva", 409)
        record = get_record(model, identifier)
        data, ownerships = extract_ownerships(data) if model is Property else (data, None)
        data, guarantor_ids = extract_guarantors(data) if model is RentalContract else (data, None)
        original_data = data
        tenant_ids = None
        if model is RentalContract:
            from app.services.contract_service import ContractService
            data, tenant_ids = ContractService.extract_tenants(data, record)
        values = payload(model, data)
        lock_parent_properties(record, values)
        record = get_record(model, identifier, lock=True)
        if model is RentalContract:
            # Recheck membership after obtaining the financial operation locks.
            data, tenant_ids = ContractService.extract_tenants(original_data, record)
            values = payload(model, data)
        check_overlap = isinstance(record, RentalContract) and any(
            key in {"property_id", "start_date", "end_date", "status"} and value != getattr(record, key)
            for key, value in values.items())
        if isinstance(record, RentalContract) and record.charges:
            protected = {"property_id", "tenant_id", "currency", "start_date", "end_date"}
            if any(key in protected and value != getattr(record, key) for key, value in values.items()):
                raise APIError("No se puede cambiar la identidad o período de un contrato con mensualidades", 409)
        for key, value in values.items():
            setattr(record, key, value)
        with db.session.no_autoflush:
            validate(record, check_overlap=check_overlap)
        db.session.flush()
        if model is Property:
            sync_ownerships(record, ownerships)
        if model is RentalContract:
            ContractService.sync_tenants(record, tenant_ids)
            sync_guarantors(record, guarantor_ids)
        return record

    @staticmethod
    @transactional
    def delete(resource, identifier):
        model = RESOURCES[resource]
        if model in FINANCIAL:
            raise APIError("No se permite borrar operaciones financieras; utilice anulación", 409)
        record = get_record(model, identifier)
        lock_parent_properties(record, {})
        record = get_record(model, identifier, lock=True)
        if isinstance(record, RentalContractTenant):
            contract = get_record(RentalContract, record.contract_id, lock=True)
            if record.person_id == contract.tenant_id or contract.charges:
                raise APIError("No se puede eliminar el inquilino principal o cambiar inquilinos con mensualidades", 409)
        for relationship in inspect(model).relationships:
            if model is RentalContract and relationship.key in {"tenant_links", "guarantor_links"}:
                continue
            if relationship.uselist and getattr(record, relationship.key):
                raise APIError("El registro tiene operaciones relacionadas y no puede borrarse", 409)
        Repository.delete(record)


def period(record):
    if not 1 <= record.period_month <= 12 or not 1 <= record.period_year <= 9999:
        raise APIError("Período inválido")
    return date(record.period_year, record.period_month, 1)


def replay(model, values):
    key = values.get("idempotency_key")
    if not key:
        raise APIError("idempotency_key es obligatorio")
    existing = db.session.scalar(select(model).where(model.idempotency_key == key))
    if existing:
        if existing.cancelled_at or any(getattr(existing, k) != v for k, v in values.items()):
            raise APIError("La clave de idempotencia ya se utilizó para otra operación", 409)
        return existing
    return None


class FinanceService:
    @staticmethod
    def lock_property_for_contract(contract_id):
        contract = get_record(RentalContract, contract_id)
        get_record(Property, contract.property_id, lock=True)
        return get_record(RentalContract, contract_id, lock=True)

    @staticmethod
    def active_settlements(property_id, year, month, currency):
        return list(db.session.scalars(select(OwnerSettlement).where(
            OwnerSettlement.property_id == property_id,
            OwnerSettlement.period_year == year, OwnerSettlement.period_month == month,
            OwnerSettlement.currency == currency, OwnerSettlement.cancelled_at.is_(None))))

    @staticmethod
    def create(resource, data):
        return getattr(FinanceService, f"create_{resource}")(data)

    @staticmethod
    def create_charges(data):
        values = payload(RentCharge, data, {"total_amount", "status", "currency", "administration_percentage"})
        values = {**DEFAULTS[RentCharge], **values}
        contract = FinanceService.lock_property_for_contract(values.get("contract_id"))
        if contract.status != "active":
            raise APIError("El contrato no está activo", 409)
        values["currency"] = contract.currency
        values["administration_percentage"] = contract.administration_percentage or ZERO
        record = RentCharge(**values)
        if record.period_year is None or record.period_month is None:
            raise APIError("period_year y period_month son obligatorios")
        start = period(record)
        end = date(start.year, start.month, calendar.monthrange(start.year, start.month)[1])
        if end < contract.start_date or start > contract.end_date:
            raise APIError("El período no corresponde al contrato")
        if record.rent_amount is None:
            adjustment = db.session.scalar(select(RentAdjustment).where(
                RentAdjustment.contract_id == contract.id,
                RentAdjustment.effective_date <= start).order_by(RentAdjustment.effective_date.desc(), RentAdjustment.id.desc()))
            record.rent_amount = adjustment.new_amount if adjustment else contract.current_rent
        record.total_amount = record.rent_amount + record.other_charges - record.discounts
        if record.total_amount < 0:
            raise APIError("Los descuentos superan el importe de la mensualidad")
        validate(record)
        if not contract.start_date <= record.due_date <= contract.end_date:
            raise APIError("due_date debe estar dentro de las fechas del contrato")
        Repository.add(record)
        record.status = record.calculated_status
        return record

    @staticmethod
    def create_payments(data):
        values = payload(RentPayment, data)
        existing = replay(RentPayment, values)
        if existing:
            return existing
        charge = get_record(RentCharge, values.get("charge_id"))
        FinanceService.lock_property_for_contract(charge.contract_id)
        charge = get_record(RentCharge, charge.id, lock=True)
        if values.get("contract_id") != charge.contract_id:
            raise APIError("El pago y la mensualidad deben pertenecer al mismo contrato")
        record = RentPayment(**values)
        validate(record)
        if charge.cancelled_at:
            raise APIError("La mensualidad está anulada", 409)
        if record.amount <= 0 or record.amount > charge.outstanding_balance:
            raise APIError("El pago debe ser positivo y no superar el saldo pendiente", 409)
        if record.payment_date > business_today() or record.payment_date < charge.contract.start_date:
            raise APIError("La fecha del pago debe estar entre el inicio del contrato y hoy")
        Repository.add(record)
        db.session.expire(charge, ["payments"])
        charge.status = charge.calculated_status
        return record

    @staticmethod
    def create_settlements(data):
        values = payload(OwnerSettlement, data, {"net_amount", "status", "ownership_percentage"})
        existing = replay(OwnerSettlement, values)
        if existing:
            return existing
        values = {**DEFAULTS[OwnerSettlement], **values}
        property = get_record(Property, values.get("property_id"), lock=True)
        owner = db.session.scalar(select(PropertyOwner).where(
            PropertyOwner.property_id == property.id, PropertyOwner.person_id == values.get("owner_id")))
        if owner is None or owner.ownership_percentage <= 0:
            raise APIError("La persona no es propietaria de este inmueble")
        values["ownership_percentage"] = owner.ownership_percentage
        record = OwnerSettlement(**values)
        if record.period_year is None or record.period_month is None:
            raise APIError("period_year y period_month son obligatorios")
        period(record)
        charges = list(db.session.scalars(select(RentCharge).join(RentalContract).where(
            RentalContract.property_id == property.id, RentCharge.period_year == record.period_year,
            RentCharge.period_month == record.period_month, RentCharge.currency == record.currency,
            RentCharge.cancelled_at.is_(None))))
        if record.settlement_date is None:
            raise APIError("settlement_date es obligatorio")
        # A backdated settlement cannot spend receipts recorded with later dates.
        receipts = {c.id: sum((p.amount for p in c.payments
                    if p.cancelled_at is None and p.payment_date <= record.settlement_date), ZERO)
                    for c in charges}
        collected = sum(receipts.values(), ZERO)
        settlements = FinanceService.active_settlements(property.id, record.period_year, record.period_month, record.currency)
        allocated = sum((s.gross_amount for s in settlements), ZERO)
        owner_allocated = sum((s.gross_amount for s in settlements if s.owner_id == owner.person_id), ZERO)
        owner_limit = money(collected * owner.ownership_percentage / Decimal("100"))
        available = min(collected - allocated, owner_limit - owner_allocated)
        if record.gross_amount is None:
            record.gross_amount = max(available, ZERO)
        if record.gross_amount <= 0 or record.gross_amount > available:
            raise APIError("La liquidación supera lo cobrado disponible para el propietario", 409)
        if record.administration_fee is None:
            fees = sum((receipts[c.id] * min(c.rent_amount, c.total_amount) / c.total_amount * c.administration_percentage / Decimal("100") if c.total_amount else ZERO for c in charges), ZERO)
            record.administration_fee = money(record.gross_amount * fees / collected)
        record.net_amount = record.gross_amount - record.administration_fee - record.deductions
        if record.net_amount < 0:
            raise APIError("Honorarios y deducciones superan el importe bruto")
        validate(record)
        if record.settlement_date > business_today():
            raise APIError("No se pueden registrar liquidaciones futuras")
        Repository.add(record)
        record.status = record.calculated_status
        return record

    @staticmethod
    def create_transfers(data):
        values = payload(OwnerTransfer, data)
        existing = replay(OwnerTransfer, values)
        if existing:
            return existing
        settlement = get_record(OwnerSettlement, values.get("settlement_id"))
        get_record(Property, settlement.property_id, lock=True)
        settlement = get_record(OwnerSettlement, settlement.id, lock=True)
        record = OwnerTransfer(**values)
        validate(record)
        if settlement.cancelled_at:
            raise APIError("La liquidación está anulada", 409)
        if record.amount <= 0 or record.amount > settlement.outstanding_balance:
            raise APIError("La transferencia debe ser positiva y no superar el saldo", 409)
        if record.transfer_date < settlement.settlement_date or record.transfer_date > business_today():
            raise APIError("Fecha de transferencia inválida")
        Repository.add(record)
        db.session.expire(settlement, ["transfers"])
        settlement.status = settlement.calculated_status
        return record

    @staticmethod
    @transactional
    def cancel(resource, identifier, data):
        model = RESOURCES[resource]
        if model not in FINANCIAL:
            raise APIError("Este recurso no admite anulación")
        if not isinstance(data, dict) or set(data) != {"reason"} or not isinstance(data["reason"], str) or not data["reason"].strip():
            raise APIError("Se requiere un motivo de anulación (reason)")
        record = get_record(model, identifier)
        if isinstance(record, (RentCharge, RentPayment)):
            FinanceService.lock_property_for_contract(record.contract_id)
        else:
            property_id = record.property_id if isinstance(record, OwnerSettlement) else record.settlement.property_id
            get_record(Property, property_id, lock=True)
        record = get_record(model, identifier, lock=True)
        if record.cancelled_at:
            return record
        if isinstance(record, RentCharge) and record.paid_amount > 0:
            raise APIError("Primero deben anularse los pagos de la mensualidad", 409)
        if isinstance(record, RentPayment):
            charge = get_record(RentCharge, record.charge_id, lock=True)
            settlements = FinanceService.active_settlements(charge.contract.property_id, charge.period_year, charge.period_month, charge.currency)
            if settlements:
                raise APIError("Primero deben anularse las liquidaciones del período", 409)
        if isinstance(record, OwnerSettlement) and record.transferred_amount > 0:
            raise APIError("Primero deben anularse las transferencias", 409)
        record.cancelled_at = utcnow()
        record.cancellation_reason = data["reason"].strip()
        if isinstance(record, (RentCharge, OwnerSettlement)):
            record.status = "cancelled"
        db.session.flush()
        if isinstance(record, RentPayment):
            db.session.expire(record.charge, ["payments"])
            record.charge.status = record.charge.calculated_status
        if isinstance(record, OwnerTransfer):
            db.session.expire(record.settlement, ["transfers"])
            record.settlement.status = record.settlement.calculated_status
        return record
