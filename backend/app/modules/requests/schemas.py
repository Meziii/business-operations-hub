import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import AccountTier, AccountType, Channel, Decision, Priority, Status
from app.modules.requests.rules import SlaState


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Ref(ORMModel):
    id: uuid.UUID
    name: str


class AccountOut(ORMModel):
    id: uuid.UUID
    name: str
    type: AccountType
    tier: AccountTier


class CategoryOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    description: str
    default_team_id: uuid.UUID | None


class SlaOut(ORMModel):
    priority: Priority
    response_minutes: int
    resolution_minutes: int


class SlaUpdate(BaseModel):
    response_minutes: int = Field(gt=0, le=60 * 24 * 60)
    resolution_minutes: int = Field(gt=0, le=60 * 24 * 90)


class TeamRef(ORMModel):
    id: uuid.UUID
    code: str
    name: str


class Assignable(BaseModel):
    id: uuid.UUID
    full_name: str
    team_ids: list[uuid.UUID]


class ReferenceData(BaseModel):
    accounts: list[AccountOut]
    categories: list[CategoryOut]
    teams: list[TeamRef]
    sla: list[SlaOut]
    assignees: list[Assignable]
    ai_provider: str


class RequestCreate(BaseModel):
    account_id: uuid.UUID
    channel: Channel
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=10_000)


class RequestUpdate(BaseModel):
    """Champs modifiables. Les clés absentes ne changent pas ; `null` vide le champ."""

    title: str | None = Field(default=None, min_length=5, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=10_000)
    priority: Priority | None = None
    category_id: uuid.UUID | None = None
    team_id: uuid.UUID | None = None
    assignee_id: uuid.UUID | None = None


class TransitionIn(BaseModel):
    status: Status
    comment: str | None = Field(default=None, max_length=5000)


class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class UserRef(ORMModel):
    id: uuid.UUID
    full_name: str


class RequestRow(BaseModel):
    id: uuid.UUID
    reference: str
    title: str
    status: Status
    priority: Priority | None
    channel: Channel
    account: Ref
    category: Ref | None
    team: TeamRef | None
    assignee: UserRef | None
    created_at: datetime
    due_response_at: datetime | None
    due_resolution_at: datetime | None
    sla_state: SlaState
    sla_next_due: datetime | None


class RequestPage(BaseModel):
    items: list[RequestRow]
    total: int
    page: int
    page_size: int


class EventOut(ORMModel):
    id: int
    event_type: str
    field: str | None
    old_value: str | None
    new_value: str | None
    actor: UserRef | None
    created_at: datetime


class CommentOut(ORMModel):
    id: uuid.UUID
    body: str
    author: UserRef | None
    created_at: datetime


class AttachmentOut(ORMModel):
    id: uuid.UUID
    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    uploaded_by: UserRef | None
    created_at: datetime


class SuggestionOut(ORMModel):
    id: uuid.UUID
    proposal: dict[str, Any]
    explanation: str
    confidence: float
    provider: str
    latency_ms: int
    decision: Decision
    final_value: dict[str, Any] | None
    decided_by: UserRef | None
    decided_at: datetime | None
    created_at: datetime


class RequestDetail(RequestRow):
    description: str
    account_tier: AccountTier
    created_by: UserRef | None
    first_response_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    updated_at: datetime
    can_edit: bool
    allowed_transitions: list[Status]
    comments: list[CommentOut]
    attachments: list[AttachmentOut]
    events: list[EventOut]
    suggestion: SuggestionOut | None


class DecisionIn(BaseModel):
    """`accept` applique la proposition, `modify` applique les valeurs envoyées, `reject` n'applique rien."""

    action: Literal["accept", "modify", "reject"]
    category_id: uuid.UUID | None = None
    priority: Priority | None = None
    team_id: uuid.UUID | None = None
    reason: str | None = Field(default=None, max_length=500)


class TeamLoad(BaseModel):
    team: TeamRef
    open: int
    overdue: int
    unassigned: int


class RequestStats(BaseModel):
    open: int
    overdue: int
    to_classify: int
    waiting_info: int
    resolved_last_7_days: int
    by_status: dict[str, int]
    by_team: list[TeamLoad]
    ai_decisions: dict[str, int]


class FieldScore(BaseModel):
    field: str
    correct: int
    total: int
    accuracy: float


class ConfusionCell(BaseModel):
    expected: str
    predicted: str
    count: int


class EvaluationReport(BaseModel):
    provider: str
    dataset: str
    split: str
    size: int
    fields: list[FieldScore]
    all_three_correct: float
    mean_latency_ms: float
    category_confusion: list[ConfusionCell]
    errors: list[dict[str, str]]


class LiveQuality(BaseModel):
    decided: int
    accepted: int
    modified: int
    rejected: int
    field_kept: dict[str, float]


class QualityOut(BaseModel):
    offline: EvaluationReport
    dev_all_three_correct: float
    live: LiveQuality
