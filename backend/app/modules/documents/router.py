"""Module 2 — API du traitement documentaire. Chaque route contrôle les droits côté serveur (NFR-01).

Lecture : tous les rôles de l'organisation. Dépôt, correction, décision, rattachement : ADMIN, MANAGER, AGENT.
"""

import threading
import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CurrentUser, DbSession, require_roles
from app.models import (
    AiSuggestion,
    Anomaly,
    Decision,
    DocStatus,
    DocType,
    Document,
    Extraction,
    Role,
    ServiceRequest,
    User,
)
from app.modules.documents import service
from app.modules.documents.evaluate import evaluate
from app.modules.documents.extract import MockDocumentExtractor
from app.modules.documents.fields import FIELDS, as_doc_type
from app.modules.documents.schemas import (
    AnomalyOut,
    DocQualityOut,
    DocumentDetail,
    DocumentPage,
    DocumentRow,
    DocumentStats,
    ExtractionReport,
    FieldOut,
    FieldsUpdate,
    LinkIn,
    LiveDocQuality,
    RejectIn,
    RequestRef,
    UserRef,
    VersionOut,
)
from app.modules.requests.rules import can_view

router = APIRouter(prefix="/api", tags=["documents"])

Writer = Annotated[User, Depends(require_roles(Role.ADMIN, Role.MANAGER, Role.AGENT))]
Manager = Annotated[User, Depends(require_roles(Role.ADMIN, Role.MANAGER))]


def get_document(db: Session, user: User, doc_id: uuid.UUID) -> Document:
    doc = db.get(Document, doc_id)
    if doc is None or doc.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document introuvable.")
    return doc


def visible_request(db: Session, user: User, request_id: uuid.UUID | None) -> ServiceRequest | None:
    if request_id is None:
        return None
    req = db.get(ServiceRequest, request_id)
    if req is None or not can_view(user, req):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Demande introuvable.")
    return req


def _summary(doc_type: DocType, data: dict[str, Any]) -> str:
    if doc_type == DocType.INVOICE:
        parts = [data.get("invoice_number"), data.get("supplier_name")]
    else:
        parts = [data.get("product_reference"), data.get("customer_name")]
    return " · ".join(p for p in parts if p) or "Champs à compléter"


def _counts(db: Session, doc_ids: list[uuid.UUID]) -> dict[tuple[uuid.UUID, str], int]:
    if not doc_ids:
        return {}
    rows = db.execute(
        select(Anomaly.document_id, Anomaly.severity, func.count())
        .where(Anomaly.document_id.in_(doc_ids))
        .group_by(Anomaly.document_id, Anomaly.severity)
    )
    return {(d, s): n for d, s, n in rows}


def to_row(doc: Document, data: dict[str, Any], counts: dict[tuple[uuid.UUID, str], int]) -> DocumentRow:
    return DocumentRow(
        id=doc.id,
        reference=doc.reference,
        doc_type=doc.doc_type,
        status=doc.status,
        filename=doc.filename,
        summary=_summary(doc.doc_type, data),
        amount=data.get("total_incl_tax") if doc.doc_type == DocType.INVOICE else None,
        blocking=counts.get((doc.id, "BLOCKING"), 0),
        warnings=counts.get((doc.id, "WARNING"), 0),
        ocr_used=doc.ocr_pages > 0,
        request=RequestRef.model_validate(doc.request) if doc.request else None,
        uploaded_by=UserRef.model_validate(doc.uploaded_by) if doc.uploaded_by else None,
        created_at=doc.created_at,
    )


def to_detail(db: Session, doc: Document, user: User) -> DocumentDetail:
    versions = list(
        db.scalars(select(Extraction).where(Extraction.document_id == doc.id).order_by(Extraction.version))
    )
    first, current = versions[0], versions[-1]
    anomalies = list(db.scalars(select(Anomaly).where(Anomaly.document_id == doc.id).order_by(Anomaly.id)))
    counts = {(doc.id, s): sum(a.severity == s for a in anomalies) for s in ("BLOCKING", "WARNING")}
    suggestion = service.suggestion_for(db, doc.id)
    out_versions = []
    for prev, v in zip([None, *versions[:-1]], versions, strict=True):
        changed = [k for k in v.data if prev is None or v.data[k] != prev.data.get(k)] if prev else []
        out_versions.append(
            VersionOut(
                version=v.version,
                source=v.source.value,
                provider=v.provider,
                created_at=v.created_at,
                created_by=UserRef.model_validate(v.created_by) if v.created_by else None,
                changed=changed,
            )
        )
    return DocumentDetail(
        **to_row(doc, current.data, counts).model_dump(),
        size_bytes=doc.size_bytes,
        page_count=doc.page_count,
        ocr_pages=doc.ocr_pages,
        ocr_confidence=doc.ocr_confidence,
        text=doc.text,
        text_error=doc.text_error,
        provider=first.provider,
        fields=[
            FieldOut(
                name=f.name,
                label=f.label,
                kind=f.kind,
                required=f.required,
                value=current.data.get(f.name),
                proposed=first.data.get(f.name),
                confidence=current.confidence.get(f.name, 0.0),
                corrected=current.data.get(f.name) != first.data.get(f.name),
            )
            for f in FIELDS[as_doc_type(doc.doc_type.value)]
        ],
        anomalies=[AnomalyOut.model_validate(a) for a in anomalies],
        versions=out_versions,
        decision=suggestion.decision if suggestion else None,
        decided_by=UserRef.model_validate(doc.decided_by) if doc.decided_by else None,
        decided_at=doc.decided_at,
        rejection_reason=doc.rejection_reason,
        can_edit=user.role != Role.VIEWER and doc.status == DocStatus.TO_REVIEW,
    )


def _latest_data(db: Session, doc_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, Any]]:
    if not doc_ids:
        return {}
    latest = (
        select(Extraction.document_id, func.max(Extraction.version).label("v"))
        .where(Extraction.document_id.in_(doc_ids))
        .group_by(Extraction.document_id)
        .subquery()
    )
    rows = db.execute(
        select(Extraction.document_id, Extraction.data).join(
            latest, (Extraction.document_id == latest.c.document_id) & (Extraction.version == latest.c.v)
        )
    )
    return {d: data for d, data in rows}


@router.get("/documents", response_model=DocumentPage)
def list_documents(
    user: CurrentUser,
    db: DbSession,
    status_: Annotated[DocStatus | None, Query(alias="status")] = None,
    doc_type: DocType | None = None,
    blocking_only: bool = False,
    q: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> DocumentPage:
    stmt = select(Document).where(Document.organization_id == user.organization_id)
    if status_:
        stmt = stmt.where(Document.status == status_)
    if doc_type:
        stmt = stmt.where(Document.doc_type == doc_type)
    if blocking_only:
        stmt = stmt.where(
            Document.status == DocStatus.TO_REVIEW,
            Document.id.in_(select(Anomaly.document_id).where(Anomaly.severity == "BLOCKING")),
        )
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Document.reference.ilike(pattern),
                Document.filename.ilike(pattern),
                Document.id.in_(
                    select(Extraction.document_id).where(cast(Extraction.data, String).ilike(pattern))
                ),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    docs = list(
        db.scalars(
            stmt.order_by(Document.status != DocStatus.TO_REVIEW, Document.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    ids = [d.id for d in docs]
    data, counts = _latest_data(db, ids), _counts(db, ids)
    return DocumentPage(
        items=[to_row(d, data.get(d.id, {}), counts) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/documents/stats", response_model=DocumentStats)
def document_stats(user: CurrentUser, db: DbSession) -> DocumentStats:
    org = Document.organization_id == user.organization_id
    counts = select(Document.status, func.count()).where(org).group_by(Document.status)
    by_status: dict[DocStatus, int] = {s: n for s, n in db.execute(counts)}
    with_blocking = db.scalar(
        select(func.count()).where(
            org,
            Document.status == DocStatus.TO_REVIEW,
            Document.id.in_(select(Anomaly.document_id).where(Anomaly.severity == "BLOCKING")),
        )
    )
    return DocumentStats(
        to_review=by_status.get(DocStatus.TO_REVIEW, 0),
        with_blocking=with_blocking or 0,
        validated=by_status.get(DocStatus.VALIDATED, 0),
        rejected=by_status.get(DocStatus.REJECTED, 0),
    )


@router.post("/documents", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
async def upload_document(
    user: Writer,
    db: DbSession,
    file: Annotated[UploadFile, File()],
    doc_type: Annotated[DocType, Form()],
    request_id: Annotated[uuid.UUID | None, Form()] = None,
) -> DocumentDetail:
    limit = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    request = visible_request(db, user, request_id)
    doc = service.ingest(db, user, data, file.filename or "document.pdf", doc_type, request)
    db.commit()
    db.refresh(doc)
    return to_detail(db, doc, user)


@router.get("/documents/{doc_id}", response_model=DocumentDetail)
def get_detail(doc_id: uuid.UUID, user: CurrentUser, db: DbSession) -> DocumentDetail:
    return to_detail(db, get_document(db, user, doc_id), user)


@router.get("/documents/{doc_id}/file")
def document_file(doc_id: uuid.UUID, user: CurrentUser, db: DbSession) -> FileResponse:
    doc = get_document(db, user, doc_id)
    path = Path(get_settings().storage_dir) / doc.storage_key
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fichier introuvable sur le serveur.")
    return FileResponse(
        path, media_type="application/pdf", filename=doc.filename, content_disposition_type="inline"
    )


@router.patch("/documents/{doc_id}/fields", response_model=DocumentDetail)
def correct_fields(doc_id: uuid.UUID, body: FieldsUpdate, user: Writer, db: DbSession) -> DocumentDetail:
    doc = get_document(db, user, doc_id)
    service.correct(db, doc, user, body.data)
    db.commit()
    db.refresh(doc)
    return to_detail(db, doc, user)


@router.post("/documents/{doc_id}/validate", response_model=DocumentDetail)
def validate_document(doc_id: uuid.UUID, user: Writer, db: DbSession) -> DocumentDetail:
    doc = get_document(db, user, doc_id)
    service.validate(db, doc, user)
    db.commit()
    db.refresh(doc)
    return to_detail(db, doc, user)


@router.post("/documents/{doc_id}/reject", response_model=DocumentDetail)
def reject_document(doc_id: uuid.UUID, body: RejectIn, user: Writer, db: DbSession) -> DocumentDetail:
    doc = get_document(db, user, doc_id)
    service.reject(db, doc, user, body.reason)
    db.commit()
    db.refresh(doc)
    return to_detail(db, doc, user)


@router.put("/documents/{doc_id}/request", response_model=DocumentDetail)
def link_document(doc_id: uuid.UUID, body: LinkIn, user: Writer, db: DbSession) -> DocumentDetail:
    doc = get_document(db, user, doc_id)
    service.link(db, doc, user, visible_request(db, user, body.request_id))
    db.commit()
    db.refresh(doc)
    return to_detail(db, doc, user)


_REPORTS: dict[str, ExtractionReport] = {}
_REPORTS_LOCK = threading.Lock()


def _report(split: str) -> ExtractionReport:
    """Évaluation du mode démonstration, calculée une fois par processus (OCR coûteux, ~1 min).

    Le verrou évite de lancer deux calculs en parallèle : le second attend puis réutilise le cache.
    En pratique le cache est rempli au démarrage (warm_quality_reports), donc l'appel est immédiat.
    """
    with _REPORTS_LOCK:
        if split not in _REPORTS:
            _REPORTS[split] = evaluate(MockDocumentExtractor(), split)
        return _REPORTS[split]


def warm_quality_reports() -> None:
    """Pré-calcule les rapports d'évaluation hors-ligne, pour que la page Qualité réponde vite."""
    for split in ("test", "dev"):
        _report(split)


@router.get("/ai/extraction/quality", response_model=DocQualityOut)
def extraction_quality(user: Manager, db: DbSession) -> DocQualityOut:
    org = user.organization_id
    suggestions = list(
        db.scalars(
            select(AiSuggestion).where(
                AiSuggestion.organization_id == org,
                AiSuggestion.kind == service.EXTRACTION_KIND,
                AiSuggestion.decision != Decision.PENDING,
            )
        )
    )
    decisions = {d: sum(s.decision == d for s in suggestions) for d in Decision}
    applied = [
        s for s in suggestions if s.decision in (Decision.ACCEPTED, Decision.MODIFIED) and s.final_value
    ]
    kept: dict[str, list[bool]] = {}
    for s in applied:
        final = s.final_value or {}
        for name, value in s.proposal.items():
            if value is not None or final.get(name) is not None:
                kept.setdefault(name, []).append(final.get(name) == value)
    return DocQualityOut(
        offline=_report("test"),
        dev_documents_fully_correct=_report("dev").documents_fully_correct,
        live=LiveDocQuality(
            decided=len(suggestions),
            accepted=decisions[Decision.ACCEPTED],
            modified=decisions[Decision.MODIFIED],
            rejected=decisions[Decision.REJECTED],
            field_kept={k: round(sum(v) / len(v), 3) for k, v in sorted(kept.items())},
        ),
    )
