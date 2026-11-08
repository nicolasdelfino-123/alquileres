"""Allow expenses without a description."""
from alembic import op
import sqlalchemy as sa

revision = "d41b67f524de"
down_revision = "c30a56e413cd"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("expenses") as batch:
        batch.alter_column("description", existing_type=sa.Text(), nullable=True)


def downgrade():
    op.execute("UPDATE expenses SET description = category WHERE description IS NULL")
    with op.batch_alter_table("expenses") as batch:
        batch.alter_column("description", existing_type=sa.Text(), nullable=False)
