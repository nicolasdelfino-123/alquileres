from sqlalchemy import or_, select
from app.extensions import db
from app.models import RentalContract, RentalContractTenant


class ContractRepository:
    @staticmethod
    def overlapping(record):
        statement = select(RentalContract.id).where(
            RentalContract.property_id == record.property_id,
            RentalContract.status == "active",
            RentalContract.start_date <= record.end_date,
            RentalContract.end_date >= record.start_date,
        )
        if record.id is not None:
            statement = statement.where(RentalContract.id != record.id)
        return db.session.scalar(statement.limit(1))

    @staticmethod
    def for_tenant(identifier, filters):
        statement = select(RentalContract).where(or_(
            RentalContract.tenant_id == identifier,
            RentalContract.tenant_links.any(RentalContractTenant.person_id == identifier),
        )).order_by(RentalContract.id)
        for field, value in filters.items():
            statement = statement.where(getattr(RentalContract, field) == value)
        return list(db.session.scalars(statement))
