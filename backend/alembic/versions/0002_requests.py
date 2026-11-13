"""Module 1 : clients et partenaires, catégories, SLA, demandes, historique, échanges, suggestions IA.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PRIORITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
STATUSES = ("NEW", "CLASSIFIED", "ASSIGNED", "IN_PROGRESS", "WAITING_INFO", "RESOLVED", "CLOSED")
CHANNELS = ("EMAIL", "PHONE", "PORTAL", "PARTNER")
DECISIONS = ("PENDING", "ACCEPTED", "MODIFIED", "REJECTED")


def _id() -> sa.Column[sa.Uuid]:
    return sa.Column("id", sa.Uuid(), primary_key=True)


def _timestamps() -> list[sa.Column[sa.DateTime]]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def _fk(name: str, target: str, ondelete: str, nullable: bool = True) -> sa.Column[sa.Uuid]:
    return sa.Column(name, sa.Uuid(), sa.ForeignKey(target, ondelete=ondelete), nullable=nullable)


def _org() -> sa.Column[sa.Uuid]:
    return _fk("organization_id", "organizations.id", "CASCADE", nullable=False)


def upgrade() -> None:
    op.create_table(
        "accounts",
        _id(),
        _org(),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("organization_id", "name"),
        sa.CheckConstraint("type IN ('CUSTOMER', 'PARTNER')", name="ck_accounts_type"),
        sa.CheckConstraint("tier IN ('STANDARD', 'PREMIUM')", name="ck_accounts_tier"),
    )
    op.create_index("ix_accounts_organization_id", "accounts", ["organization_id"])

    op.create_table(
        "categories",
        _id(),
        _org(),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        _fk("default_team_id", "teams.id", "SET NULL"),
        *_timestamps(),
        sa.UniqueConstraint("organization_id", "code"),
    )
    op.create_index("ix_categories_organization_id", "categories", ["organization_id"])

    op.create_table(
        "sla_policies",
        _id(),
        _org(),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("response_minutes", sa.Integer(), nullable=False),
        sa.Column("resolution_minutes", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("organization_id", "priority"),
        sa.CheckConstraint(f"priority IN {PRIORITIES}", name="ck_sla_priority"),
        sa.CheckConstraint(
            "response_minutes > 0 AND resolution_minutes >= response_minutes", name="ck_sla_delays"
        ),
    )
    op.create_index("ix_sla_policies_organization_id", "sla_policies", ["organization_id"])

    op.create_table(
        "requests",
        _id(),
        _org(),
        sa.Column("reference", sa.String(30), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("priority", sa.String(20)),
        _fk("account_id", "accounts.id", "RESTRICT", nullable=False),
        _fk("category_id", "categories.id", "SET NULL"),
        _fk("team_id", "teams.id", "SET NULL"),
        _fk("assignee_id", "users.id", "SET NULL"),
        _fk("created_by_id", "users.id", "SET NULL"),
        sa.Column("due_response_at", sa.DateTime(timezone=True)),
        sa.Column("due_resolution_at", sa.DateTime(timezone=True)),
        sa.Column("first_response_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("organization_id", "reference"),
        sa.CheckConstraint(f"status IN {STATUSES}", name="ck_requests_status"),
        sa.CheckConstraint(f"priority IN {PRIORITIES}", name="ck_requests_priority"),
        sa.CheckConstraint(f"channel IN {CHANNELS}", name="ck_requests_channel"),
    )
    op.create_index("ix_requests_organization_id", "requests", ["organization_id"])
    op.create_index("ix_requests_status", "requests", ["status"])
    op.create_index("ix_requests_team_id", "requests", ["team_id"])

    op.create_table(
        "request_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        _fk("request_id", "requests.id", "CASCADE", nullable=False),
        _fk("actor_id", "users.id", "SET NULL"),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("field", sa.String(40)),
        sa.Column("old_value", sa.String(300)),
        sa.Column("new_value", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_request_events_request_id", "request_events", ["request_id"])

    op.create_table(
        "comments",
        _id(),
        _fk("request_id", "requests.id", "CASCADE", nullable=False),
        _fk("author_id", "users.id", "SET NULL"),
        sa.Column("body", sa.Text(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_comments_request_id", "comments", ["request_id"])

    op.create_table(
        "attachments",
        _id(),
        _fk("request_id", "requests.id", "CASCADE", nullable=False),
        _fk("uploaded_by_id", "users.id", "SET NULL"),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_attachments_request_id", "attachments", ["request_id"])

    op.create_table(
        "ai_suggestions",
        _id(),
        _org(),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("proposal", postgresql.JSONB(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("provider", sa.String(60), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("final_value", postgresql.JSONB()),
        _fk("decided_by_id", "users.id", "SET NULL"),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint(f"decision IN {DECISIONS}", name="ck_ai_suggestions_decision"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_ai_suggestions_confidence"),
    )
    op.create_index("ix_ai_suggestions_organization_id", "ai_suggestions", ["organization_id"])
    op.create_index("ix_ai_suggestions_target_id", "ai_suggestions", ["target_id"])


def downgrade() -> None:
    for table in (
        "ai_suggestions",
        "attachments",
        "comments",
        "request_events",
        "requests",
        "sla_policies",
        "categories",
        "accounts",
    ):
        op.drop_table(table)
