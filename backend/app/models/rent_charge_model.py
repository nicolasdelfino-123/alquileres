from datetime import date
from app.extensions import db
from app.models.common import business_today, CancellationMixin, ZERO


class RentCharge(CancellationMixin, db.Model):
    __tablename__ = "rent_charges"
    __table_args__ = (
        db.Index('ix_charges_period_currency','period_year','period_month','currency'),
        db.UniqueConstraint("id", "contract_id", name="uq_charge_id_contract"),
        db.UniqueConstraint("contract_id", "period_year", "period_month", name="uq_charge_contract_period"),
        db.CheckConstraint("period_month BETWEEN 1 AND 12 AND period_year BETWEEN 1 AND 9999", name="ck_charge_period"),
        db.CheckConstraint("rent_amount >= 0 AND other_charges >= 0 AND discounts >= 0 AND total_amount >= 0", name="ck_charge_amounts"),
        db.CheckConstraint("total_amount = rent_amount + other_charges - discounts", name="ck_charge_total"),
        db.CheckConstraint("administration_percentage BETWEEN 0 AND 100", name="ck_charge_administration"),
        db.CheckConstraint("status IN ('pending', 'partial', 'paid', 'overdue', 'cancelled')", name="ck_charge_status"),
    )
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("rental_contracts.id"), nullable=False, index=True)
    period_year = db.Column(db.Integer, nullable=False)
    period_month = db.Column(db.Integer, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    rent_amount = db.Column(db.Numeric(12, 2), nullable=False)
    other_charges = db.Column(db.Numeric(12, 2), nullable=False, default=ZERO)
    discounts = db.Column(db.Numeric(12, 2), nullable=False, default=ZERO)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="ARS")
    administration_percentage = db.Column(db.Numeric(5, 2), nullable=False, default=ZERO)
    status = db.Column(db.String(30), nullable=False, default="pending")
    notes = db.Column(db.Text)
    contract = db.relationship("RentalContract", back_populates="charges")
    payments = db.relationship("RentPayment", back_populates="charge")

    @property
    def paid_amount(self):
        return sum((p.amount for p in self.payments if p.cancelled_at is None), ZERO)

    @property
    def outstanding_balance(self):
        return ZERO if self.cancelled_at else self.total_amount - self.paid_amount

    @property
    def calculated_status(self):
        if self.cancelled_at:
            return "cancelled"
        if self.outstanding_balance == 0:
            return "paid"
        if self.paid_amount > 0:
            return "partial"
        return "overdue" if self.due_date < business_today() else "pending"
