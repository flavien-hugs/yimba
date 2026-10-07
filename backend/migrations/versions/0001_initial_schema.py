"""initial schema: watches, mentions, collection runs, watch alerts

Revision ID: 0001
Revises:
Create Date: 2026-10-06
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collection_runs",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("watch_id", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched", sa.Integer(), nullable=False),
        sa.Column("stored", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_collection_runs_started_at"), "collection_runs", ["started_at"], unique=False)
    op.create_index(op.f("ix_collection_runs_watch_id"), "collection_runs", ["watch_id"], unique=False)
    op.create_table(
        "mentions",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("watch_id", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("author_ref", sa.String(length=32), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("likes", sa.Integer(), nullable=False),
        sa.Column("shares", sa.Integer(), nullable=False),
        sa.Column("views", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("sentiment_positive", sa.Float(), nullable=False),
        sa.Column("sentiment_neutral", sa.Float(), nullable=False),
        sa.Column("sentiment_negative", sa.Float(), nullable=False),
        sa.Column("sentiment_label", sa.String(length=10), nullable=False),
        sa.Column("emotion", sa.String(length=10), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("watch_id", "content_hash", name="uq_mentions_content"),
        sa.UniqueConstraint("watch_id", "source", "external_id", name="uq_mentions_source_item"),
    )
    op.create_index(op.f("ix_mentions_published_at"), "mentions", ["published_at"], unique=False)
    op.create_index(op.f("ix_mentions_sentiment_label"), "mentions", ["sentiment_label"], unique=False)
    op.create_index(op.f("ix_mentions_watch_id"), "mentions", ["watch_id"], unique=False)
    op.create_table(
        "watch_alerts",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("watch_id", sa.String(length=32), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mentions", sa.Integer(), nullable=False),
        sa.Column("negative", sa.Integer(), nullable=False),
        sa.Column("negative_share", sa.Float(), nullable=False),
        sa.Column("threshold_share", sa.Float(), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=14), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_watch_alerts_triggered_at"), "watch_alerts", ["triggered_at"], unique=False)
    op.create_index(op.f("ix_watch_alerts_watch_id"), "watch_alerts", ["watch_id"], unique=False)
    op.create_table(
        "watches",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("keywords", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.Column("sources", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.Column("languages", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.Column("countries", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.Column("frequency_minutes", sa.Integer(), nullable=False),
        sa.Column("alert_negative_share", sa.Float(), nullable=False),
        sa.Column("alert_min_mentions", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_watches_active"), "watches", ["active"], unique=False)
    op.create_index(op.f("ix_watches_owner_id"), "watches", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_watches_owner_id"), table_name="watches")
    op.drop_index(op.f("ix_watches_active"), table_name="watches")
    op.drop_table("watches")
    op.drop_index(op.f("ix_watch_alerts_watch_id"), table_name="watch_alerts")
    op.drop_index(op.f("ix_watch_alerts_triggered_at"), table_name="watch_alerts")
    op.drop_table("watch_alerts")
    op.drop_index(op.f("ix_mentions_watch_id"), table_name="mentions")
    op.drop_index(op.f("ix_mentions_sentiment_label"), table_name="mentions")
    op.drop_index(op.f("ix_mentions_published_at"), table_name="mentions")
    op.drop_table("mentions")
    op.drop_index(op.f("ix_collection_runs_watch_id"), table_name="collection_runs")
    op.drop_index(op.f("ix_collection_runs_started_at"), table_name="collection_runs")
    op.drop_table("collection_runs")
