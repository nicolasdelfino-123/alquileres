from app.extensions import db


class Expense(db.Model):
    __tablename__ = "expenses"
    __table_args__ = (db.CheckConstraint("amount >= 0", name="ck_expense_amount"),)
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), index=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("rental_contracts.id"), index=True)
    expense_date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="ARS")
    responsible_party = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.Text)
    property = db.relationship("Property", back_populates="expenses")
    contract = db.relationship("RentalContract", back_populates="expenses")
