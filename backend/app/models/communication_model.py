from app.extensions import db
from app.models.common import utcnow


class Communication(db.Model):
    __tablename__ = 'communications'
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('rental_contracts.id'), nullable=False, index=True)
    person_id = db.Column(db.Integer, db.ForeignKey('persons.id'), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    channel = db.Column(db.String(20), nullable=False, default='email')
    purpose = db.Column(db.String(30), nullable=False)
    payload = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default='pending')
    scheduled_at = db.Column(db.DateTime, nullable=False)
    available_at = db.Column(db.DateTime, nullable=False)
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    last_error = db.Column(db.String(64))
    __table_args__ = (db.Index('ix_communications_due','status','available_at'),)
    contract = db.relationship('RentalContract', back_populates='communications')
    person = db.relationship('Person', back_populates='communications')
