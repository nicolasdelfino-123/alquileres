"""Month attribution for uploaded receipts."""
from alembic import op
import sqlalchemy as sa
revision='f63d89b746fa'
down_revision='e52c78a635ef'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('documents',sa.Column('period_year',sa.Integer(),nullable=True))
    op.add_column('documents',sa.Column('period_month',sa.Integer(),nullable=True))
    with op.batch_alter_table('documents') as batch:
        batch.create_check_constraint('ck_document_period', '(period_year IS NULL AND period_month IS NULL) OR (period_year IS NOT NULL AND period_month IS NOT NULL AND period_year BETWEEN 1 AND 9999 AND period_month BETWEEN 1 AND 12)')
    op.create_index('ix_document_contract_period','documents',['contract_id','period_year','period_month'])

def downgrade():
    op.drop_index('ix_document_contract_period',table_name='documents')
    with op.batch_alter_table('documents') as batch:
        batch.drop_constraint('ck_document_period',type_='check')
        batch.drop_column('period_month')
        batch.drop_column('period_year')
