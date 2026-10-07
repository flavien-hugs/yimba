"""raw items: provider payloads, kept for re-mapping and purged after a retention period

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-06
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_items",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_id", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id", name="uq_raw_items_source_item"),
    )
    op.create_index(op.f("ix_raw_items_last_seen_at"), "raw_items", ["last_seen_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_raw_items_last_seen_at"), table_name="raw_items")
    op.drop_table("raw_items")
