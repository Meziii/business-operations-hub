"""Module 2 — Traitement documentaire : documents, versions d'extraction, anomalies."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Identity,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin
from app.models.core import User
from app.models.requests import ServiceRequest


def _enum(cls: type[StrEnum], name: str) -> Enum:
    return Enum(cls, name=name, native_enum=False, length=20)


class DocType(StrEnum):
    INVOICE = "INVOICE"
    WARRANTY_CLAIM = "WARRANTY_CLAIM"


class DocStatus(StrEnum):
    TO_REVIEW = "TO_REVIEW"  # extraction faite (ou impossible), en attente de vérification humaine
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"


class ExtractionSource(StrEnum):
    AI = "AI"  # proposition du fournisseur (règles ou modèle)
    HUMAN = "HUMAN"  # correction d'un collaborateur


class Document(IdMixin, TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("organization_id", "reference"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    reference: Mapped[str] = mapped_column(String(30))
    doc_type: Mapped[DocType] = mapped_column(_enum(DocType, "doc_type"))
    status: Mapped[DocStatus] = mapped_column(
        _enum(DocStatus, "doc_status"), default=DocStatus.TO_REVIEW, index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    storage_key: Mapped[str] = mapped_column(String(255))
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text, default="")
    ocr_pages: Mapped[int] = mapped_column(Integer, default=0)
    ocr_confidence: Mapped[float | None] = mapped_column(Float)
    text_error: Mapped[str | None] = mapped_column(Text)
    duplicate_key: Mapped[str | None] = mapped_column(
        String(300), index=True
    )  # RC-05, mise à jour à chaque version
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("requests.id", ondelete="SET NULL"), index=True
    )
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decided_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    is_synthetic: Mapped[bool] = mapped_column(default=False)

    request: Mapped[ServiceRequest | None] = relationship()
    uploaded_by: Mapped[User | None] = relationship(foreign_keys=[uploaded_by_id])
    decided_by: Mapped[User | None] = relationship(foreign_keys=[decided_by_id])


class Extraction(Base):
    """Une version des champs : la proposition (AI) puis chaque correction (HUMAN). Jamais modifiée."""

    __tablename__ = "extractions"
    __table_args__ = (UniqueConstraint("document_id", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    source: Mapped[ExtractionSource] = mapped_column(_enum(ExtractionSource, "extraction_source"))
    provider: Mapped[str] = mapped_column(String(60))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    confidence: Mapped[dict[str, float]] = mapped_column(JSONB)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    created_by: Mapped[User | None] = relationship()


class Anomaly(Base):
    """Résultat des contrôles sur la dernière version (recalculé à chaque version)."""

    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(10))
    field: Mapped[str | None] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(String(300))
