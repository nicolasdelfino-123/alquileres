from app.extensions import db
from app.models.common import utcnow, ZERO


class SaleOperation(db.Model):
    __tablename__ = "sale_operations"
    __table_args__ = (
        db.CheckConstraint("price >= 0 AND commission >= 0 AND commission <= price", name="ck_sale_amounts"),
        db.CheckConstraint("buyer_id <> seller_id", name="ck_sale_parties"),
        db.CheckConstraint("status IN ('pending', 'completed', 'cancelled')", name="ck_sale_status"),
    )

    operation_description = db.Column(db.String(250), nullable=True)
    agent_name = db.Column(db.String(150), nullable=True)
    personal_commission = db.Column(db.Numeric(12, 2), nullable=True)
    agency_commission = db.Column(db.Numeric(12, 2), nullable=True)
    lead_source = db.Column(db.String(150), nullable=True)
    shared_with = db.Column(db.String(150), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=True, index=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey("persons.id"), nullable=True, index=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("persons.id"), nullable=True, index=True)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="ARS")
    sale_date = db.Column(db.Date, nullable=False)
    commission = db.Column(db.Numeric(12, 2), nullable=False, default=ZERO)
    status = db.Column(db.String(30), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    property = db.relationship("Property", back_populates="sale_operations")
    buyer = db.relationship("Person", back_populates="purchases", foreign_keys=[buyer_id])
    seller = db.relationship("Person", back_populates="sales", foreign_keys=[seller_id])
