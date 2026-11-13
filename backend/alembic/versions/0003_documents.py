"""Module 2 : documents, versions d'extraction, anomalies.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _fk(name: str, target: str, ondelete: str, nullable: bool = True) -> sa.Column[sa.Uuid]:
    return sa.Column(name, sa.Uuid(), sa.ForeignKey(target, ondelete=ondelete), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _fk("organization_id", "organizations.id", "CASCADE", nullable=False),
        sa.Column("reference", sa.String(30), nullable=False),
        sa.Column("doc_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("ocr_pages", sa.Integer(), nullable=False),
        sa.Column("ocr_confidence", sa.Float()),
        sa.Column("text_error", sa.Text()),
        sa.Column("duplicate_key", sa.String(300)),
        _fk("request_id", "requests.id", "SET NULL"),
        _fk("uploaded_by_id", "users.id", "SET NULL"),
        _fk("decided_by_id", "users.id", "SET NULL"),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "reference"),
        sa.CheckConstraint("doc_type IN ('INVOICE', 'WARRANTY_CLAIM')", name="ck_documents_doc_type"),
        sa.CheckConstraint("status IN ('TO_REVIEW', 'VALIDATED', 'REJECTED')", name="ck_documents_status"),
    )
    for col in ("organization_id", "status", "sha256", "request_id", "duplicate_key"):
        op.create_index(f"ix_documents_{col}", "documents", [col])

    op.create_table(
        "extractions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _fk("document_id", "documents.id", "CASCADE", nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("provider", sa.String(60), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("confidence", postgresql.JSONB(), nullable=False),
        _fk("created_by_id", "users.id", "SET NULL"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("document_id", "version"),
        sa.CheckConstraint("source IN ('AI', 'HUMAN')", name="ck_extractions_source"),
    )
    op.create_index("ix_extractions_document_id", "extractions", ["document_id"])

    op.create_table(
        "anomalies",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        _fk("document_id", "documents.id", "CASCADE", nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("field", sa.String(40)),
        sa.Column("message", sa.String(300), nullable=False),
        sa.CheckConstraint("severity IN ('BLOCKING', 'WARNING')", name="ck_anomalies_severity"),
    )
    op.create_index("ix_anomalies_document_id", "anomalies", ["document_id"])


def downgrade() -> None:
    for table in ("anomalies", "extractions", "documents"):
        op.drop_table(table)
