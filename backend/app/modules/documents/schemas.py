import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import Decision, DocStatus, DocType


class UserRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    full_name: str


class RequestRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    reference: str
    title: str


class FieldOut(BaseModel):
    name: str
    label: str
    kind: str
    required: bool
    value: Any
    proposed: Any  # valeur de la proposition initiale, pour comparer
    confidence: float
    corrected: bool


class AnomalyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    severity: str
    field: str | None
    message: str


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    version: int
    source: str
    provider: str
    created_at: datetime
    created_by: UserRef | None
    changed: list[str]


class DocumentRow(BaseModel):
    id: uuid.UUID
    reference: str
    doc_type: DocType
    status: DocStatus
    filename: str
    summary: str
    amount: float | None
    blocking: int
    warnings: int
    ocr_used: bool
    request: RequestRef | None
    uploaded_by: UserRef | None
    created_at: datetime


class DocumentPage(BaseModel):
    items: list[DocumentRow]
    total: int
    page: int
    page_size: int


class DocumentDetail(DocumentRow):
    size_bytes: int
    page_count: int
    ocr_pages: int
    ocr_confidence: float | None
    text: str
    text_error: str | None
    provider: str
    fields: list[FieldOut]
    anomalies: list[AnomalyOut]
    versions: list[VersionOut]
    decision: Decision | None
    decided_by: UserRef | None
    decided_at: datetime | None
    rejection_reason: str | None
    can_edit: bool


class DocumentStats(BaseModel):
    to_review: int
    with_blocking: int
    validated: int
    rejected: int


class FieldsUpdate(BaseModel):
    data: dict[str, Any]


class RejectIn(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class LinkIn(BaseModel):
    request_id: uuid.UUID | None


class FieldScore(BaseModel):
    field: str
    label: str
    correct: int
    total: int
    accuracy: float


class AnomalyScore(BaseModel):
    expected: int
    detected: int
    false_alarms: int


class ExtractionReport(BaseModel):
    provider: str
    split: str
    size: int
    evaluated: int
    skipped_scans: int
    fields: list[FieldScore]
    documents_fully_correct: float
    text_accuracy: float | None
    scan_accuracy: float | None
    by_layout: dict[str, float]
    anomalies: AnomalyScore
    errors: list[dict[str, str]]


class LiveDocQuality(BaseModel):
    decided: int
    accepted: int
    modified: int
    rejected: int
    field_kept: dict[str, float]


class DocQualityOut(BaseModel):
    offline: ExtractionReport
    dev_documents_fully_correct: float
    live: LiveDocQuality
