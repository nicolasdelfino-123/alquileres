from app.extensions import db
from app.models.common import CancellationMixin


class OwnerTransfer(CancellationMixin, db.Model):
    __tablename__ = "owner_transfers"
    __table_args__ = (
        db.CheckConstraint("amount > 0", name="ck_transfer_positive"),
        db.UniqueConstraint("reference", name="uq_transfer_reference"),
        db.UniqueConstraint("idempotency_key", name="uq_transfer_idempotency"),
    )
    confirmed_at = db.Column(db.DateTime, nullable=True)

    id = db.Column(db.Integer, primary_key=True)
    settlement_id = db.Column(db.Integer, db.ForeignKey("owner_settlements.id"), nullable=False, index=True)
    transfer_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    reference = db.Column(db.String(150), nullable=False)
    idempotency_key = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.Text)
    settlement = db.relationship("OwnerSettlement", back_populates="transfers")
