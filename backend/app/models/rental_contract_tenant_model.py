from app.extensions import db


class RentalContractTenant(db.Model):
    __tablename__ = "rental_contract_tenants"
    __table_args__ = (
        db.UniqueConstraint("contract_id", "person_id", name="uq_contract_tenant"),
    )

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("rental_contracts.id"), nullable=False, index=True)
    person_id = db.Column(db.Integer, db.ForeignKey("persons.id"), nullable=False, index=True)

    contract = db.relationship("RentalContract", back_populates="tenant_links")
    person = db.relationship("Person", back_populates="contract_tenancies")
