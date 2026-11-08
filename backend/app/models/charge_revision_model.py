from app.extensions import db
from app.models.common import utcnow


class ChargeRevision(db.Model):
    __tablename__ = 'charge_revisions'
    id = db.Column(db.Integer, primary_key=True)
    charge_id = db.Column(db.Integer, db.ForeignKey('rent_charges.id'), nullable=False, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.String(500), nullable=False)
    previous_data = db.Column(db.JSON, nullable=False)
    new_data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
