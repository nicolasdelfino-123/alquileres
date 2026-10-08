from app.extensions import db
from app.models.common import utcnow


class Reminder(db.Model):
    __tablename__ = "reminders"
    __table_args__ = (db.CheckConstraint("status IN ('pending', 'completed', 'cancelled')", name="ck_reminder_status"),)
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("rental_contracts.id"), index=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="pending")
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    contract = db.relationship("RentalContract", back_populates="reminders")
    property = db.relationship("Property", back_populates="reminders")
