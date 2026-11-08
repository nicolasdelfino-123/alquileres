"""Transactional email outbox and shared auth limits.

Revision ID: b29f45d302bc
Revises: a18e34c291ab
"""
from alembic import op
import sqlalchemy as sa
revision = "b29f45d302bc"
down_revision = "a18e34c291ab"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("mail_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(150), nullable=False),
        sa.Column("credentials", sa.Text(), nullable=False),
        sa.Column("registration_code", sa.Text()),
        sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_table("mail_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token_id", sa.Integer(), sa.ForeignKey("auth_tokens.id"), nullable=False, unique=True),
        sa.Column("payload", sa.Text()),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("last_error", sa.String(64)))
    op.create_index("ix_mail_outbox_due", "mail_outbox", ["status", "available_at"])
    op.create_table("auth_rate_buckets",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False))
    op.create_index("ix_auth_rate_buckets_expires_at", "auth_rate_buckets", ["expires_at"])


def downgrade():
    op.drop_table("mail_settings")
    op.drop_table("auth_rate_buckets")
    op.drop_table("mail_outbox")
