"""Email verification and password recovery.

Revision ID: a18e34c291ab
Revises: 4969671c1a5a
"""
from alembic import op
import sqlalchemy as sa
revision = "a18e34c291ab"
down_revision = "4969671c1a5a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("email_pending", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0"))
    op.create_table("auth_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("digest", sa.String(64), unique=True, nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime()))
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"])


def downgrade():
    op.drop_table("auth_tokens")
    op.drop_column("users", "auth_version")
    op.drop_column("users", "email_pending")
