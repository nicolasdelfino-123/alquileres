from decimal import Decimal

from app.extensions import db


class PropertyOwner(db.Model):
    __tablename__ = "property_owners"
    __table_args__ = (
        db.UniqueConstraint("property_id", "person_id", name="uq_property_owner"),
        db.CheckConstraint(
            "ownership_percentage >= 0 AND ownership_percentage <= 100",
            name="ck_property_owners_ownership_percentage",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey("persons.id"), nullable=False)
    ownership_percentage = db.Column(
        db.Numeric(5, 2), nullable=False, default=Decimal("100.00")
    )
    notes = db.Column(db.Text, nullable=True)

    property = db.relationship("Property", back_populates="owners")
    person = db.relationship("Person", back_populates="property_ownerships")
