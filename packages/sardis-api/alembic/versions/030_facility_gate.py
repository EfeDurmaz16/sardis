"""Facility Gate append-only event store

Revision ID: 030
Revises: 029
Create Date: 2026-04-24 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "030"
down_revision: str | None = "029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "facility_events",
        sa.Column("event_id", sa.String(length=64), primary_key=True),
        sa.Column("organization_id", sa.String(length=128), nullable=False),
        sa.Column("aggregate_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=96), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=True),
        sa.Column("actor_id", sa.String(length=128), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("previous_event_hash", sa.String(length=64), nullable=True),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_facility_events_org_aggregate", "facility_events", ["organization_id", "aggregate_id", "occurred_at"])
    op.create_index("idx_facility_events_type", "facility_events", ["event_type"])
    op.create_unique_constraint(
        "uq_facility_events_idempotency",
        "facility_events",
        ["organization_id", "idempotency_key"],
    )

    op.create_table(
        "facility_request_states",
        sa.Column("request_id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=128), nullable=False),
        sa.Column("facility_id", sa.String(length=128), nullable=False),
        sa.Column("agent_id", sa.String(length=128), nullable=False),
        sa.Column("mandate_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("latest_decision_id", sa.String(length=128), nullable=True),
        sa.Column("latest_verdict", sa.String(length=64), nullable=True),
        sa.Column("merchant", sa.String(length=255), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=12), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_facility_request_states_org", "facility_request_states", ["organization_id", "updated_at"])

    op.create_table(
        "facility_records",
        sa.Column("facility_id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=128), nullable=False),
        sa.Column("sponsor_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=96), nullable=False),
        sa.Column("facility_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("limit_payload", sa.JSON(), nullable=False),
        sa.Column("allowed_categories", sa.JSON(), nullable=False),
        sa.Column("allowed_merchants", sa.JSON(), nullable=False),
        sa.Column("blocked_merchants", sa.JSON(), nullable=False),
        sa.Column("approval_threshold_minor", sa.BigInteger(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_facility_records_org_sponsor", "facility_records", ["organization_id", "sponsor_id"])
    op.create_index("idx_facility_records_status", "facility_records", ["status"])

    op.create_table(
        "facility_policy_records",
        sa.Column("policy_record_id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=128), nullable=False),
        sa.Column("facility_id", sa.String(length=128), nullable=False),
        sa.Column("policy_version", sa.String(length=128), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint(
        "uq_facility_policy_records_version",
        "facility_policy_records",
        ["organization_id", "facility_id", "policy_version"],
    )
    op.create_index("idx_facility_policy_records_latest", "facility_policy_records", ["organization_id", "facility_id", "created_at"])

    op.create_table(
        "facility_mandate_records",
        sa.Column("mandate_record_id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=128), nullable=False),
        sa.Column("mandate_id", sa.String(length=128), nullable=False),
        sa.Column("agent_id", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint(
        "uq_facility_mandate_records_version",
        "facility_mandate_records",
        ["organization_id", "mandate_id", "agent_id", "version"],
    )
    op.create_index(
        "idx_facility_mandate_records_lookup",
        "facility_mandate_records",
        ["organization_id", "mandate_id", "agent_id", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_facility_mandate_records_lookup", table_name="facility_mandate_records")
    op.drop_constraint("uq_facility_mandate_records_version", "facility_mandate_records", type_="unique")
    op.drop_table("facility_mandate_records")
    op.drop_index("idx_facility_policy_records_latest", table_name="facility_policy_records")
    op.drop_constraint("uq_facility_policy_records_version", "facility_policy_records", type_="unique")
    op.drop_table("facility_policy_records")
    op.drop_index("idx_facility_records_status", table_name="facility_records")
    op.drop_index("idx_facility_records_org_sponsor", table_name="facility_records")
    op.drop_table("facility_records")
    op.drop_index("idx_facility_request_states_org", table_name="facility_request_states")
    op.drop_table("facility_request_states")
    op.drop_constraint("uq_facility_events_idempotency", "facility_events", type_="unique")
    op.drop_index("idx_facility_events_type", table_name="facility_events")
    op.drop_index("idx_facility_events_org_aggregate", table_name="facility_events")
    op.drop_table("facility_events")
