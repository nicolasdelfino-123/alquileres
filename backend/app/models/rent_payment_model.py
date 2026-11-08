from app.extensions import db
from app.models.common import CancellationMixin


class RentPayment(CancellationMixin, db.Model):
    __tablename__ = "rent_payments"
    __table_args__ = (
        db.Index('ix_payments_date','payment_date'),
        db.CheckConstraint("amount > 0", name="ck_payment_positive"),
        db.UniqueConstraint("reference", name="uq_payment_reference"),
        db.UniqueConstraint("idempotency_key", name="uq_payment_idempotency"),
        db.ForeignKeyConstraint(["charge_id", "contract_id"], ["rent_charges.id", "rent_charges.contract_id"], name="fk_payment_charge_contract"),
    )
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("rental_contracts.id"), nullable=False, index=True)
    charge_id = db.Column(db.Integer, nullable=False, index=True)
    payment_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    reference = db.Column(db.String(150), nullable=False)
    idempotency_key = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.Text)
    contract = db.relationship("RentalContract", back_populates="payments", foreign_keys=[contract_id], overlaps="payments")
    charge = db.relationship("RentCharge", back_populates="payments", foreign_keys=[charge_id, contract_id], overlaps="contract,payments")
