"""Service responsibilities and idempotent monthly control reminders."""
from alembic import op
import sqlalchemy as sa
revision = 'e52c78a635ef'
down_revision = 'd41b67f524de'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('properties', sa.Column('utility_rules', sa.JSON(), nullable=True))
    op.add_column('rental_contracts', sa.Column('utility_rules', sa.JSON(), nullable=True))
    with op.batch_alter_table('reminders') as batch:
        batch.add_column(sa.Column('source_key', sa.String(150), nullable=True))
        batch.create_unique_constraint('uq_reminder_source_key', ['source_key'])

def downgrade():
    with op.batch_alter_table('reminders') as batch:
        batch.drop_constraint('uq_reminder_source_key', type_='unique')
        batch.drop_column('source_key')
    op.drop_column('rental_contracts', 'utility_rules')
    op.drop_column('properties', 'utility_rules')
