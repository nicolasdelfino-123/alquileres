from sqlalchemy import select
from app.extensions import db
from app.models import Person, Property, RentalContract, RentalContractTenant
from app.repositories.contract_repository import ContractRepository
from app.services.management_service import APIError, convert, get_record, serialize


class ContractService:
    @staticmethod
    def extract_tenants(data, current=None):
        if not isinstance(data, dict):
            raise APIError("Se requiere un objeto JSON")
        values = dict(data)
        tenant_ids = values.pop("tenant_ids", None)
        if "tenant_ids" in data:
            if not isinstance(tenant_ids, list) or not tenant_ids:
                raise APIError("tenant_ids debe ser una lista no vacía")
            tenant_ids = [convert(Person.__table__.c.id, identifier) for identifier in tenant_ids]
            if any(identifier is None or identifier <= 0 for identifier in tenant_ids) or len(set(tenant_ids)) != len(tenant_ids):
                raise APIError("tenant_ids debe contener identificadores positivos sin duplicados")
            primary = convert(Person.__table__.c.id, values["tenant_id"]) if "tenant_id" in values else None
            if primary is None:
                primary = current.tenant_id if current and current.tenant_id in tenant_ids else tenant_ids[0]
            if primary not in tenant_ids:
                raise APIError("tenant_id debe pertenecer a tenant_ids")
            values["tenant_id"] = primary
        elif "tenant_id" in values:
            primary = convert(Person.__table__.c.id, values["tenant_id"])
            tenant_ids = [primary]
            if current:
                tenant_ids += [identifier for identifier in current.tenant_ids if identifier != current.tenant_id and identifier != primary]
        for identifier in tenant_ids or []:
            get_record(Person, identifier)
        if current and tenant_ids is not None and current.charges and set(tenant_ids) != set(current.tenant_ids):
            raise APIError("No se pueden cambiar los inquilinos de un contrato con mensualidades", 409)
        return values, tenant_ids

    @staticmethod
    def validate_overlap(record):
        if record.status != "active":
            return
        get_record(Property, record.property_id, lock=True)
        if ContractRepository.overlapping(record) is not None:
            raise APIError("Existe otro contrato activo superpuesto para esta propiedad", 409)

    @staticmethod
    def sync_tenants(record, identifiers):
        if identifiers is None:
            return
        desired = set(identifiers)
        existing = {link.person_id: link for link in record.tenant_links}
        for identifier, link in existing.items():
            if identifier not in desired:
                db.session.delete(link)
        for identifier in desired - existing.keys():
            db.session.add(RentalContractTenant(contract=record, person_id=identifier))
        db.session.flush()
        db.session.expire(record, ["tenant_links"])

    @staticmethod
    def validate_link(record):
        contract = get_record(RentalContract, record.contract_id, lock=True)
        if contract.charges and record.person_id not in contract.tenant_ids:
            raise APIError("No se pueden cambiar los inquilinos de un contrato con mensualidades", 409)
        duplicate = db.session.scalar(select(RentalContractTenant.id).where(
            RentalContractTenant.contract_id == record.contract_id,
            RentalContractTenant.person_id == record.person_id,
            RentalContractTenant.id != record.id if record.id is not None else True,
        ))
        if duplicate is not None:
            raise APIError("El inquilino ya está asociado al contrato", 409)

    @staticmethod
    def tenants(identifier):
        contract = get_record(RentalContract, identifier)
        return {"contract_id": contract.id, "tenant_id": contract.tenant_id,
                "tenant_ids": contract.tenant_ids,
                "tenants": [serialize(get_record(Person, person_id)) for person_id in contract.tenant_ids]}
