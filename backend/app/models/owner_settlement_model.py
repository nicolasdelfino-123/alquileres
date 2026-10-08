from builtins import property as computed_property
from app.extensions import db
from app.models.common import CancellationMixin, ZERO


class OwnerSettlement(CancellationMixin, db.Model):
    __tablename__ = "owner_settlements"
    __table_args__ = (
        db.CheckConstraint("period_month BETWEEN 1 AND 12 AND period_year BETWEEN 1 AND 9999", name="ck_settlement_period"),
        db.CheckConstraint("gross_amount >= 0 AND administration_fee >= 0 AND deductions >= 0 AND net_amount >= 0", name="ck_settlement_amounts"),
        db.CheckConstraint("net_amount = gross_amount - administration_fee - deductions", name="ck_settlement_net"),
        db.CheckConstraint("status IN ('pending', 'partial', 'transferred', 'cancelled')", name="ck_settlement_status"),
        db.CheckConstraint("ownership_percentage BETWEEN 0 AND 100", name="ck_settlement_ownership"),
        db.UniqueConstraint("idempotency_key", name="uq_settlement_idempotency"),
    )
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("persons.id"), nullable=False, index=True)
    period_year = db.Column(db.Integer, nullable=False)
    period_month = db.Column(db.Integer, nullable=False)
    gross_amount = db.Column(db.Numeric(12, 2), nullable=False)
    administration_fee = db.Column(db.Numeric(12, 2), nullable=False, default=ZERO)
    deductions = db.Column(db.Numeric(12, 2), nullable=False, default=ZERO)
    net_amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="ARS")
    ownership_percentage = db.Column(db.Numeric(5, 2), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="pending")
    settlement_date = db.Column(db.Date, nullable=False)
    idempotency_key = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.Text)
    property = db.relationship("Property", back_populates="settlements")
    owner = db.relationship("Person", back_populates="settlements")
    transfers = db.relationship("OwnerTransfer", back_populates="settlement")

    @computed_property
    def transferred_amount(self):
        return sum((t.amount for t in self.transfers if t.cancelled_at is None), ZERO)

    @computed_property
    def outstanding_balance(self):
        return ZERO if self.cancelled_at else self.net_amount - self.transferred_amount

    @computed_property
    def calculated_status(self):
        if self.cancelled_at:
            return "cancelled"
        if self.outstanding_balance == 0:
            return "transferred"
        return "partial" if self.transferred_amount else "pending"
