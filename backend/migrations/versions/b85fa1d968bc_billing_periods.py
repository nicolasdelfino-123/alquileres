"""Explicit calendar/anniversary periods and mid-period adjustment treatment."""
from alembic import op
import sqlalchemy as sa
revision = 'b85fa1d968bc'
down_revision = 'a74e90c857ab'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('rental_contracts', sa.Column('billing_cycle', sa.String(20), nullable=False, server_default='calendar'))
    op.add_column('rental_contracts', sa.Column('adjustment_billing_treatment', sa.String(20)))
    op.add_column('rent_adjustments', sa.Column('billing_treatment', sa.String(20)))
    op.add_column('rent_charges', sa.Column('billing_start', sa.Date()))
    op.add_column('rent_charges', sa.Column('billing_end', sa.Date()))
    op.add_column('rent_charges', sa.Column('rent_calculation', sa.JSON()))


def downgrade():
    with op.batch_alter_table('rent_charges') as batch:
        for column in ('rent_calculation', 'billing_end', 'billing_start'):
            batch.drop_column(column)
    with op.batch_alter_table('rent_adjustments') as batch:
        batch.drop_column('billing_treatment')
    with op.batch_alter_table('rental_contracts') as batch:
        batch.drop_column('adjustment_billing_treatment')
        batch.drop_column('billing_cycle')
