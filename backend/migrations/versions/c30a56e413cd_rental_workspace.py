"""Optional property data, guarantors and operational rental fields.

Revision ID: c30a56e413cd
Revises: b29f45d302bc
"""
from alembic import op
import sqlalchemy as sa
revision = "c30a56e413cd"
down_revision = "b29f45d302bc"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("charge_revisions",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("charge_id",sa.Integer(),sa.ForeignKey("rent_charges.id"),nullable=False),
        sa.Column("created_by_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("reason",sa.String(500),nullable=False),
        sa.Column("previous_data",sa.JSON(),nullable=False),
        sa.Column("new_data",sa.JSON(),nullable=False),
        sa.Column("created_at",sa.DateTime(),nullable=False))
    op.create_index("ix_charge_revisions_charge_id","charge_revisions",["charge_id"])
    op.create_index('ix_payments_date','rent_payments',['payment_date'])
    op.create_index('ix_expenses_date_currency','expenses',['expense_date', 'currency'])
    op.create_index('ix_settlements_period_currency','owner_settlements',['period_year', 'period_month', 'currency'])
    op.create_index('ix_charges_period_currency','rent_charges',['period_year', 'period_month', 'currency'])
    with op.batch_alter_table("sale_operations") as batch:
        for key in ("property_id", "buyer_id", "seller_id"):
            batch.alter_column(key, existing_type=sa.Integer(), nullable=True)
        batch.add_column(sa.Column("operation_description", sa.String(250), nullable=True))
        batch.add_column(sa.Column("agent_name", sa.String(150), nullable=True))
        batch.add_column(sa.Column("personal_commission", sa.Numeric(12,2), nullable=True))
        batch.add_column(sa.Column("agency_commission", sa.Numeric(12,2), nullable=True))
        batch.add_column(sa.Column("lead_source", sa.String(150), nullable=True))
        batch.add_column(sa.Column("shared_with", sa.String(150), nullable=True))
        batch.add_column(sa.Column("notes", sa.Text(), nullable=True))
    op.create_table("communications",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("contract_id",sa.Integer(),sa.ForeignKey("rental_contracts.id"),nullable=False),
        sa.Column("person_id",sa.Integer(),sa.ForeignKey("persons.id"),nullable=False),
        sa.Column("created_by_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("channel",sa.String(20),nullable=False),
        sa.Column("purpose",sa.String(30),nullable=False),
        sa.Column("payload",sa.Text()),
        sa.Column("status",sa.String(20),nullable=False),
        sa.Column("scheduled_at",sa.DateTime(),nullable=False),
        sa.Column("available_at",sa.DateTime(),nullable=False),
        sa.Column("sent_at",sa.DateTime()),
        sa.Column("created_at",sa.DateTime(),nullable=False),
        sa.Column("attempts",sa.Integer(),nullable=False),
        sa.Column("last_error",sa.String(64)))
    op.create_index("ix_communications_due","communications",["status","available_at"])
    op.create_index("ix_communications_contract_id","communications",["contract_id"])
    op.add_column("rental_contracts", sa.Column("collection_alias", sa.String(100), nullable=True))
    op.add_column("rental_contracts", sa.Column("collection_cbu", sa.String(22), nullable=True))
    op.add_column("properties", sa.Column("property_type", sa.String(40), nullable=True))
    op.add_column("properties", sa.Column("unit", sa.String(40), nullable=True))
    op.add_column("properties", sa.Column("floor", sa.String(20), nullable=True))
    op.add_column("properties", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("properties", sa.Column("province", sa.String(100), nullable=True))
    op.add_column("properties", sa.Column("neighborhood", sa.String(100), nullable=True))
    op.add_column("properties", sa.Column("postal_code", sa.String(20), nullable=True))
    op.add_column("properties", sa.Column("registry_number", sa.String(80), nullable=True))
    op.add_column("properties", sa.Column("internal_code", sa.String(50), nullable=True))
    op.add_column("properties", sa.Column("rooms", sa.Integer, nullable=True))
    op.add_column("properties", sa.Column("bedrooms", sa.Integer, nullable=True))
    op.add_column("properties", sa.Column("bathrooms", sa.Integer, nullable=True))
    op.add_column("properties", sa.Column("total_area", sa.Numeric(12, 2), nullable=True))
    op.add_column("properties", sa.Column("covered_area", sa.Numeric(12, 2), nullable=True))
    op.add_column("properties", sa.Column("condition", sa.String(60), nullable=True))
    op.add_column("properties", sa.Column("utility_electricity", sa.String(150), nullable=True))
    op.add_column("properties", sa.Column("utility_water", sa.String(150), nullable=True))
    op.add_column("properties", sa.Column("utility_gas", sa.String(150), nullable=True))
    op.add_column("properties", sa.Column("utility_municipal", sa.String(150), nullable=True))
    op.add_column("properties", sa.Column("utility_provincial", sa.String(150), nullable=True))
    op.add_column("properties", sa.Column("notes", sa.Text, nullable=True))
    op.add_column("properties", sa.Column("agency_ownership_percentage", sa.Numeric(5, 2), nullable=True))
    op.add_column("persons", sa.Column("occupation", sa.String(150), nullable=True))
    op.add_column("persons", sa.Column("employer", sa.String(150), nullable=True))
    op.add_column("persons", sa.Column("work_phone", sa.String(30), nullable=True))
    op.add_column("persons", sa.Column("bank_name", sa.String(100), nullable=True))
    op.add_column("persons", sa.Column("bank_holder", sa.String(150), nullable=True))
    op.add_column("rental_contracts", sa.Column("payment_day", sa.Integer, nullable=True))
    op.add_column("rental_contracts", sa.Column("payment_method", sa.String(50), nullable=True))
    op.add_column("rental_contracts", sa.Column("deposit_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("rental_contracts", sa.Column("signed_date", sa.Date, nullable=True))
    op.add_column("rental_contracts", sa.Column("next_adjustment_date", sa.Date, nullable=True))
    op.add_column("rental_contracts", sa.Column("fixed_adjustment_percentage", sa.Numeric(8, 4), nullable=True))
    op.add_column("rent_adjustments", sa.Column("index_name", sa.String(50), nullable=True))
    op.add_column("rent_adjustments", sa.Column("calculation_detail", sa.Text, nullable=True))
    op.add_column("rent_adjustments", sa.Column("source_url", sa.String(500), nullable=True))
    op.add_column("owner_transfers", sa.Column("confirmed_at", sa.DateTime, nullable=True))
    op.add_column("reminders", sa.Column("category", sa.String(50), nullable=True))
    op.add_column("reminders", sa.Column("priority", sa.String(20), nullable=True))
    op.add_column("reminders", sa.Column("progress", sa.String(30), nullable=True))
    op.add_column("reminders", sa.Column("amount", sa.Numeric(12, 2), nullable=True))
    with op.batch_alter_table("reminders") as batch:
        batch.add_column(sa.Column("responsible_person_id", sa.Integer(), sa.ForeignKey("persons.id", name="fk_reminder_responsible"), nullable=True))
    op.add_column("reminders", sa.Column("next_action", sa.Text, nullable=True))
    with op.batch_alter_table("documents") as batch:
        batch.add_column(sa.Column("charge_id", sa.Integer(), sa.ForeignKey("rent_charges.id", name="fk_document_charge_id"), nullable=True))
    with op.batch_alter_table("documents") as batch:
        batch.add_column(sa.Column("payment_id", sa.Integer(), sa.ForeignKey("rent_payments.id", name="fk_document_payment_id"), nullable=True))
    with op.batch_alter_table("documents") as batch:
        batch.add_column(sa.Column("settlement_id", sa.Integer(), sa.ForeignKey("owner_settlements.id", name="fk_document_settlement_id"), nullable=True))
    with op.batch_alter_table("documents") as batch:
        batch.add_column(sa.Column("transfer_id", sa.Integer(), sa.ForeignKey("owner_transfers.id", name="fk_document_transfer_id"), nullable=True))
    op.create_table("contract_guarantors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("rental_contracts.id"), nullable=False),
        sa.Column("person_id", sa.Integer(), sa.ForeignKey("persons.id"), nullable=False),
        sa.UniqueConstraint("contract_id", "person_id", name="uq_contract_guarantor"))
    op.create_index("ix_contract_guarantors_contract_id", "contract_guarantors", ["contract_id"])
    op.create_index("ix_contract_guarantors_person_id", "contract_guarantors", ["person_id"])


def downgrade():
    op.drop_table("charge_revisions")
    op.drop_index('ix_payments_date',table_name='rent_payments')
    op.drop_index('ix_expenses_date_currency',table_name='expenses')
    op.drop_index('ix_settlements_period_currency',table_name='owner_settlements')
    op.drop_index('ix_charges_period_currency',table_name='rent_charges')
    with op.batch_alter_table("documents") as batch:
        for key in ("transfer_id", "settlement_id", "payment_id", "charge_id"):
            batch.drop_constraint("fk_document_"+key, type_="foreignkey")
            batch.drop_column(key)
    with op.batch_alter_table("reminders") as batch:
        batch.drop_constraint("fk_reminder_responsible", type_="foreignkey")
        batch.drop_column("responsible_person_id")
    with op.batch_alter_table("sale_operations") as batch:
        for key in ("operation_description","agent_name","personal_commission","agency_commission","lead_source","shared_with","notes"):
            batch.drop_column(key)
        for key in ("property_id", "buyer_id", "seller_id"):
            batch.alter_column(key, existing_type=sa.Integer(), nullable=False)
    op.drop_table("communications")
    op.drop_column("rental_contracts", "collection_alias")
    op.drop_column("rental_contracts", "collection_cbu")
    op.drop_table("contract_guarantors")
    op.drop_column("reminders", "next_action")
    op.drop_column("reminders", "amount")
    op.drop_column("reminders", "progress")
    op.drop_column("reminders", "priority")
    op.drop_column("reminders", "category")
    op.drop_column("owner_transfers", "confirmed_at")
    op.drop_column("rent_adjustments", "source_url")
    op.drop_column("rent_adjustments", "calculation_detail")
    op.drop_column("rent_adjustments", "index_name")
    op.drop_column("rental_contracts", "fixed_adjustment_percentage")
    op.drop_column("rental_contracts", "next_adjustment_date")
    op.drop_column("rental_contracts", "signed_date")
    op.drop_column("rental_contracts", "deposit_amount")
    op.drop_column("rental_contracts", "payment_method")
    op.drop_column("rental_contracts", "payment_day")
    op.drop_column("persons", "bank_holder")
    op.drop_column("persons", "bank_name")
    op.drop_column("persons", "work_phone")
    op.drop_column("persons", "employer")
    op.drop_column("persons", "occupation")
    op.drop_column("properties", "agency_ownership_percentage")
    op.drop_column("properties", "notes")
    op.drop_column("properties", "utility_provincial")
    op.drop_column("properties", "utility_municipal")
    op.drop_column("properties", "utility_gas")
    op.drop_column("properties", "utility_water")
    op.drop_column("properties", "utility_electricity")
    op.drop_column("properties", "condition")
    op.drop_column("properties", "covered_area")
    op.drop_column("properties", "total_area")
    op.drop_column("properties", "bathrooms")
    op.drop_column("properties", "bedrooms")
    op.drop_column("properties", "rooms")
    op.drop_column("properties", "internal_code")
    op.drop_column("properties", "registry_number")
    op.drop_column("properties", "postal_code")
    op.drop_column("properties", "neighborhood")
    op.drop_column("properties", "province")
    op.drop_column("properties", "city")
    op.drop_column("properties", "floor")
    op.drop_column("properties", "unit")
    op.drop_column("properties", "property_type")
