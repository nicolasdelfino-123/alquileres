from app.extensions import db
from app.models.common import utcnow


class Document(db.Model):
    __tablename__ = "documents"
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), index=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("rental_contracts.id"), index=True)
    person_id = db.Column(db.Integer, db.ForeignKey("persons.id"), index=True)
    document_type = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    notes = db.Column(db.Text)
    property = db.relationship("Property", back_populates="documents")
    contract = db.relationship("RentalContract", back_populates="documents")
    person = db.relationship("Person", back_populates="documents")
