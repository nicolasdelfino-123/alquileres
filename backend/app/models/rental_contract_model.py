from builtins import property as computed_property
from datetime import datetime, timezone

from app.extensions import db


class RentalContract(db.Model):
    utility_rules = db.Column(db.JSON, nullable=True)
    __tablename__ = "rental_contracts"
    __table_args__ = (
        db.CheckConstraint("initial_rent >= 0 AND current_rent >= 0", name="ck_contract_rents"),
        db.CheckConstraint("administration_percentage IS NULL OR administration_percentage BETWEEN 0 AND 100", name="ck_contract_administration"),
        db.CheckConstraint("adjustment_frequency_months IS NULL OR adjustment_frequency_months > 0", name="ck_contract_frequency"),
        db.CheckConstraint(
            "end_date > start_date", name="ck_rental_contracts_dates"
        ),
    )

    collection_alias = db.Column(db.String(100), nullable=True)
    collection_cbu = db.Column(db.String(22), nullable=True)
    payment_day = db.Column(db.Integer, nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    deposit_amount = db.Column(db.Numeric(12, 2), nullable=True)
    signed_date = db.Column(db.Date, nullable=True)
    next_adjustment_date = db.Column(db.Date, nullable=True)
    fixed_adjustment_percentage = db.Column(db.Numeric(8, 4), nullable=True)

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("persons.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    initial_rent = db.Column(db.Numeric(12, 2), nullable=False)
    current_rent = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), default="ARS")
    adjustment_frequency_months = db.Column(db.Integer, nullable=True)
    adjustment_index = db.Column(db.String(50), nullable=True)
    administration_percentage = db.Column(db.Numeric(5, 2), nullable=True)
    status = db.Column(db.String(30), default="active")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    property = db.relationship("Property", back_populates="rental_contracts")
    tenant = db.relationship("Person", back_populates="rental_contracts")
    adjustments = db.relationship("RentAdjustment", back_populates="contract")

    charges = db.relationship("RentCharge", back_populates="contract")
    payments = db.relationship("RentPayment", back_populates="contract", foreign_keys="RentPayment.contract_id", overlaps="charge,payments")
    expenses = db.relationship("Expense", back_populates="contract")
    documents = db.relationship("Document", back_populates="contract")
    reminders = db.relationship("Reminder", back_populates="contract")

    tenant_links = db.relationship("RentalContractTenant", back_populates="contract", cascade="all, delete-orphan")

    @computed_property
    def tenant_ids(self):
        # The original principal tenant remains valid without backfilling old rows.
        return sorted({self.tenant_id} | {link.person_id for link in self.tenant_links})

    guarantor_links = db.relationship("ContractGuarantor", back_populates="contract", cascade="all, delete-orphan")

    @computed_property
    def guarantor_ids(self):
        return sorted(link.person_id for link in self.guarantor_links)

    communications = db.relationship("Communication", back_populates="contract")
