"""users: soft delete (deleted_at); one live account per email instead of one account per email

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-07

The downgrade fails if a deleted account and a live one share an email.
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

LIVE = sa.text("deleted_at IS NULL")


def upgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        # SQLite cannot drop a constraint: batch mode rebuilds the table; the convention names the unnamed constraint.
        with op.batch_alter_table("users", naming_convention={"uq": "uq_%(table_name)s_%(column_0_name)s"}) as batch:
            batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
            batch.drop_constraint("uq_users_email", type_="unique")
    else:
        op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        op.drop_constraint("users_email_key", "users", type_="unique")
    op.create_index("ux_users_email_live", "users", ["email"], unique=True, postgresql_where=LIVE, sqlite_where=LIVE)


def downgrade() -> None:
    op.drop_index("ux_users_email_live", table_name="users")
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("users") as batch:
            batch.create_unique_constraint("uq_users_email", ["email"])
            batch.drop_column("deleted_at")
    else:
        op.create_unique_constraint("users_email_key", "users", ["email"])
        op.drop_column("users", "deleted_at")
