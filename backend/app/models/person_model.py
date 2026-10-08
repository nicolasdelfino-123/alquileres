from datetime import datetime, timezone

from app.extensions import db


class Person(db.Model):
    __tablename__ = "persons"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    dni = db.Column(db.String(20), nullable=True, unique=True)
    cuit_cuil = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    bank_alias = db.Column(db.String(100), nullable=True)
    cbu = db.Column(db.String(22), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    property_ownerships = db.relationship("PropertyOwner", back_populates="person")
    rental_contracts = db.relationship("RentalContract", back_populates="tenant")

    settlements = db.relationship("OwnerSettlement", back_populates="owner")
    documents = db.relationship("Document", back_populates="person")

    contract_tenancies = db.relationship("RentalContractTenant", back_populates="person")
    purchases = db.relationship("SaleOperation", back_populates="buyer", foreign_keys="SaleOperation.buyer_id")
    sales = db.relationship("SaleOperation", back_populates="seller", foreign_keys="SaleOperation.seller_id")

    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "dni": self.dni,
            "cuit_cuil": self.cuit_cuil,
            "phone": self.phone,
            "email": self.email,
            "address": self.address,
            "bank_alias": self.bank_alias,
            "cbu": self.cbu,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
