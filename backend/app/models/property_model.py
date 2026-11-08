from app.extensions import db

class Property(db.Model):
    utility_rules = db.Column(db.JSON, nullable=True)
    __tablename__ = "properties"

    property_type = db.Column(db.String(40), nullable=True)
    unit = db.Column(db.String(40), nullable=True)
    floor = db.Column(db.String(20), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    province = db.Column(db.String(100), nullable=True)
    neighborhood = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    registry_number = db.Column(db.String(80), nullable=True)
    internal_code = db.Column(db.String(50), nullable=True)
    rooms = db.Column(db.Integer, nullable=True)
    bedrooms = db.Column(db.Integer, nullable=True)
    bathrooms = db.Column(db.Integer, nullable=True)
    total_area = db.Column(db.Numeric(12, 2), nullable=True)
    covered_area = db.Column(db.Numeric(12, 2), nullable=True)
    condition = db.Column(db.String(60), nullable=True)
    utility_electricity = db.Column(db.String(150), nullable=True)
    utility_water = db.Column(db.String(150), nullable=True)
    utility_gas = db.Column(db.String(150), nullable=True)
    utility_municipal = db.Column(db.String(150), nullable=True)
    utility_provincial = db.Column(db.String(150), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    agency_ownership_percentage = db.Column(db.Numeric(5, 2), nullable=True)

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    operation_type = db.Column(db.String(50), nullable=False)  # alquiler / venta
    status = db.Column(db.String(50), nullable=False, default="available")

    owners = db.relationship("PropertyOwner", back_populates="property")
    rental_contracts = db.relationship("RentalContract", back_populates="property")

    settlements = db.relationship("OwnerSettlement", back_populates="property")
    expenses = db.relationship("Expense", back_populates="property")
    documents = db.relationship("Document", back_populates="property")
    reminders = db.relationship("Reminder", back_populates="property")

    sale_operations = db.relationship("SaleOperation", back_populates="property")

    def to_dict(self):
        from app.services.management_service import serialize
        return serialize(self)
