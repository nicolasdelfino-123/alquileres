"""Official index snapshots, confirmed previews and acquisition commissions."""
from alembic import op
import sqlalchemy as sa

revision = 'a74e90c857ab'
down_revision = 'f63d89b746fa'
branch_labels = None
depends_on = None


def cancellation_columns():
    return [sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('cancelled_at', sa.DateTime()), sa.Column('cancellation_reason', sa.Text())]


def upgrade():
    op.create_table('contract_fees',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('contract_id', sa.Integer(), sa.ForeignKey('rental_contracts.id'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('payer', sa.String(20), nullable=False),
        sa.Column('agreed_date', sa.Date(), nullable=False), sa.Column('notes', sa.Text()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        *cancellation_columns(),
        sa.CheckConstraint('amount > 0', name='ck_contract_fee_amount'),
        sa.CheckConstraint("payer IN ('tenant','owner')", name='ck_contract_fee_payer'))
    op.create_index('ix_contract_fees_contract_id', 'contract_fees', ['contract_id'])
    op.create_table('contract_fee_payments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('fee_id', sa.Integer(), sa.ForeignKey('contract_fees.id'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=False), sa.Column('method', sa.String(30), nullable=False),
        sa.Column('reference', sa.String(150)), sa.Column('idempotency_key', sa.String(100), nullable=False, unique=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        *cancellation_columns(), sa.CheckConstraint('amount > 0', name='ck_fee_payment_amount'))
    op.create_index('ix_contract_fee_payments_fee_id', 'contract_fee_payments', ['fee_id'])
    op.create_index('ix_contract_fee_payments_payment_date', 'contract_fee_payments', ['payment_date'])
    op.create_table('official_indices',
        sa.Column('id', sa.Integer(), primary_key=True), sa.Column('kind', sa.String(3), nullable=False),
        sa.Column('value_date', sa.Date(), nullable=False), sa.Column('value', sa.Numeric(24, 10), nullable=False),
        sa.Column('source_url', sa.String(500), nullable=False), sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('kind', 'value_date', name='uq_official_index_day'),
        sa.CheckConstraint('value > 0', name='ck_official_index_positive'))
    op.create_table('adjustment_quotes',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('contract_id', sa.Integer(), sa.ForeignKey('rental_contracts.id'), nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False), sa.Column('base_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('detail', sa.JSON(), nullable=False), sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime()))
    op.create_index('ix_adjustment_quotes_contract_id', 'adjustment_quotes', ['contract_id'])


def downgrade():
    for table in ('adjustment_quotes', 'official_indices', 'contract_fee_payments', 'contract_fees'):
        op.drop_table(table)
