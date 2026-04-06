from app.extensions import db

class Property(db.Model):
    __tablename__ = "properties"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    operation_type = db.Column(db.String(50), nullable=False)  # alquiler / venta
    status = db.Column(db.String(50), nullable=False, default="available")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "address": self.address,
            "price": float(self.price),
            "operation_type": self.operation_type,
            "status": self.status,
        }
