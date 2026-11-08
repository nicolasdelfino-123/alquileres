from app.extensions import db


class ContractGuarantor(db.Model):
    __tablename__ = "contract_guarantors"
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("rental_contracts.id"), nullable=False, index=True)
    person_id = db.Column(db.Integer, db.ForeignKey("persons.id"), nullable=False, index=True)
    __table_args__ = (db.UniqueConstraint("contract_id", "person_id", name="uq_contract_guarantor"),)
    contract = db.relationship("RentalContract", back_populates="guarantor_links")
    person = db.relationship("Person", back_populates="guarantees")
