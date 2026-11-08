from app.extensions import db


class RentAdjustment(db.Model):
    __tablename__ = "rent_adjustments"
    __table_args__ = (
        db.CheckConstraint("previous_amount >= 0 AND new_amount >= 0", name="ck_adjustment_amounts"),
        db.CheckConstraint("adjustment_percentage IS NULL OR adjustment_percentage >= 0", name="ck_adjustment_percentage"),
    )

    index_name = db.Column(db.String(50), nullable=True)
    calculation_detail = db.Column(db.Text, nullable=True)
    source_url = db.Column(db.String(500), nullable=True)

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(
        db.Integer, db.ForeignKey("rental_contracts.id"), nullable=False
    )
    effective_date = db.Column(db.Date, nullable=False)
    previous_amount = db.Column(db.Numeric(12, 2), nullable=False)
    new_amount = db.Column(db.Numeric(12, 2), nullable=False)
    adjustment_percentage = db.Column(db.Numeric(8, 4), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    contract = db.relationship("RentalContract", back_populates="adjustments")
