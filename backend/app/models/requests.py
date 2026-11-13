"""Module 1 — Demandes : clients et partenaires, paramétrage, demandes, historique, échanges, IA."""

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
from app.models.core import Team, User


def _enum(cls: type[StrEnum], name: str) -> Enum:
    return Enum(cls, name=name, native_enum=False, length=20)


class AccountType(StrEnum):
    CUSTOMER = "CUSTOMER"
    PARTNER = "PARTNER"


class AccountTier(StrEnum):
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"


class Priority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Channel(StrEnum):
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    PORTAL = "PORTAL"
    PARTNER = "PARTNER"


class Status(StrEnum):
    NEW = "NEW"
    CLASSIFIED = "CLASSIFIED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_INFO = "WAITING_INFO"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class Decision(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    MODIFIED = "MODIFIED"
    REJECTED = "REJECTED"


class Account(IdMixin, TimestampMixin, Base):
    """Client ou partenaire (revendeur, distributeur) à l'origine des demandes."""

    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("organization_id", "name"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[AccountType] = mapped_column(_enum(AccountType, "account_type"))
    tier: Mapped[AccountTier] = mapped_column(
        _enum(AccountTier, "account_tier"), default=AccountTier.STANDARD
    )
    is_synthetic: Mapped[bool] = mapped_column(default=False)


class Category(IdMixin, TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("organization_id", "code"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    default_team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"))

    default_team: Mapped[Team | None] = relationship()


class SlaPolicy(IdMixin, TimestampMixin, Base):
    """Délais par priorité, en minutes calendaires (règle RG-05)."""

    __tablename__ = "sla_policies"
    __table_args__ = (UniqueConstraint("organization_id", "priority"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    priority: Mapped[Priority] = mapped_column(_enum(Priority, "priority"))
    response_minutes: Mapped[int] = mapped_column(Integer)
    resolution_minutes: Mapped[int] = mapped_column(Integer)


class ServiceRequest(IdMixin, TimestampMixin, Base):
    """Une demande client ou partenaire (table `requests`)."""

    __tablename__ = "requests"
    __table_args__ = (UniqueConstraint("organization_id", "reference"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    reference: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    channel: Mapped[Channel] = mapped_column(_enum(Channel, "channel"))
    status: Mapped[Status] = mapped_column(_enum(Status, "request_status"), default=Status.NEW, index=True)
    priority: Mapped[Priority | None] = mapped_column(_enum(Priority, "priority"))
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"))
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    due_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_resolution_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_synthetic: Mapped[bool] = mapped_column(default=False)

    account: Mapped[Account] = relationship()
    category: Mapped[Category | None] = relationship()
    team: Mapped[Team | None] = relationship()
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id])
    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_id])


class RequestEvent(Base):
    """Historique d'une demande : qui, quoi, quand, avant / après (BR-04)."""

    __tablename__ = "request_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(String(40))
    field: Mapped[str | None] = mapped_column(String(40))
    old_value: Mapped[str | None] = mapped_column(String(300))
    new_value: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    actor: Mapped[User | None] = relationship()


class Comment(IdMixin, TimestampMixin, Base):
    __tablename__ = "comments"

    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    body: Mapped[str] = mapped_column(Text)

    author: Mapped[User | None] = relationship()


class Attachment(IdMixin, TimestampMixin, Base):
    __tablename__ = "attachments"

    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String(255))

    uploaded_by: Mapped[User | None] = relationship()


class AiSuggestion(IdMixin, TimestampMixin, Base):
    """Toute proposition de l'IA, avec la décision humaine qui la suit (BR-05)."""

    __tablename__ = "ai_suggestions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    target_type: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[uuid.UUID] = mapped_column(index=True)
    kind: Mapped[str] = mapped_column(String(30))
    proposal: Mapped[dict[str, Any]] = mapped_column(JSONB)
    explanation: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    provider: Mapped[str] = mapped_column(String(60))
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    decision: Mapped[Decision] = mapped_column(_enum(Decision, "ai_decision"), default=Decision.PENDING)
    final_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    decided_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    decided_by: Mapped[User | None] = relationship()
