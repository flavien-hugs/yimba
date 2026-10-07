"""mentions: venue, where the publication was found (publication, page, channel, hashtag)

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-07
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mentions", sa.Column("venue", sa.String(length=200), nullable=True))


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("mentions") as batch:
            batch.drop_column("venue")
    else:
        op.drop_column("mentions", "venue")
