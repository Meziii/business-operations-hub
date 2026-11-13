"""Traitement documentaire : dépôt, lecture, extraction, contrôles, correction, décision, rattachement.

Règles RD-01 à RD-08 et contrôles RC-01 à RC-09 : docs/03-processes/document-processing.md.
"""

import hashlib
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.ai import get_document_extractor
from app.audit import log_action
from app.config import get_settings
from app.models import (
    AiSuggestion,
    Anomaly,
    Decision,
    DocStatus,
    DocType,
    Document,
    Extraction,
    ExtractionSource,
    Organization,
    ServiceRequest,
    User,
)
from app.modules.documents import controls
from app.modules.documents.extract import (
    DocumentExtractor,
    ExtractionError,
    ExtractionResult,
    MockDocumentExtractor,
)
from app.modules.documents.fields import FIELDS, as_doc_type, validate_fields
from app.modules.documents.fields import DocType as FieldsDocType
from app.modules.documents.text import TextExtractionError, extract_text
from app.modules.requests.service import add_event, now

PDF_MAGIC = b"%PDF-"
EXTRACTION_KIND = "extraction"


def _unprocessable(message: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, message)


def next_reference(db: Session, org_id: uuid.UUID, year: int) -> str:
    """RD-01 : DOC-AAAA-NNNNN, séquentiel par organisation et par année."""
    db.execute(select(Organization.id).where(Organization.id == org_id).with_for_update())
    prefix = f"DOC-{year}-"
    last = db.scalar(
        select(func.max(Document.reference)).where(
            Document.organization_id == org_id, Document.reference.like(f"{prefix}%")
        )
    )
    number = int(last.rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}{number:05d}"


def check_pdf(data: bytes) -> None:
    """RD-02 (NFR-03) : PDF vérifié sur le contenu, taille plafonnée."""
    limit = get_settings().max_upload_mb * 1024 * 1024
    if len(data) > limit:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Fichier trop volumineux ({get_settings().max_upload_mb} Mo maximum).",
        )
    if not data.startswith(PDF_MAGIC):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Seuls les fichiers PDF sont acceptés.")


def latest_extraction(db: Session, doc_id: uuid.UUID) -> Extraction | None:
    return db.scalar(
        select(Extraction)
        .where(Extraction.document_id == doc_id)
        .order_by(Extraction.version.desc())
        .limit(1)
    )


def first_extraction(db: Session, doc_id: uuid.UUID) -> Extraction | None:
    return db.scalar(select(Extraction).where(Extraction.document_id == doc_id, Extraction.version == 1))


def suggestion_for(db: Session, doc_id: uuid.UUID) -> AiSuggestion | None:
    return db.scalar(
        select(AiSuggestion)
        .where(AiSuggestion.target_id == doc_id, AiSuggestion.kind == EXTRACTION_KIND)
        .limit(1)
    )


def _duplicates(db: Session, doc: Document) -> list[str]:
    """RC-05 : même fichier, ou même clé métier, sur un autre document non rejeté de l'organisation."""
    q = select(Document.reference).where(
        Document.organization_id == doc.organization_id,
        Document.id != doc.id,
        Document.status != DocStatus.REJECTED,
    )
    same_file = q.where(Document.sha256 == doc.sha256)
    refs = set(db.scalars(same_file))
    if doc.duplicate_key:
        refs |= set(db.scalars(q.where(Document.duplicate_key == doc.duplicate_key)))
    return sorted(refs)


def refresh_anomalies(db: Session, doc: Document, data: dict[str, Any]) -> list[Anomaly]:
    """Recalcule les contrôles sur la version courante (RD-05)."""
    doc_type = as_doc_type(doc.doc_type.value)
    doc.duplicate_key = controls.duplicate_key(doc_type, data)
    db.flush()
    findings = controls.check(doc_type, data, now().date(), _duplicates(db, doc))
    db.execute(delete(Anomaly).where(Anomaly.document_id == doc.id))
    rows = [
        Anomaly(document_id=doc.id, code=f.code, severity=f.severity, field=f.field, message=f.message)
        for f in findings
    ]
    db.add_all(rows)
    db.flush()
    return rows


def _run_extractor(
    extractor: DocumentExtractor, doc_type: FieldsDocType, text: str, ocr_conf: float | None
) -> ExtractionResult:
    try:
        return extractor.extract(doc_type, text, ocr_conf)
    except ExtractionError as exc:
        if isinstance(extractor, MockDocumentExtractor):
            raise
        result = MockDocumentExtractor().extract(doc_type, text, ocr_conf)
        result.provider = f"{result.provider} (repli)"
        result.notes.append(f"Repli sur les règles : {exc}")
        return result


def ingest(
    db: Session,
    actor: User,
    data: bytes,
    filename: str,
    doc_type: DocType,
    request: ServiceRequest | None = None,
    extractor: DocumentExtractor | None = None,
    is_synthetic: bool = False,
) -> Document:
    """RD-02 à RD-05 : contrôle du fichier, stockage, texte (OCR si besoin), extraction, contrôles."""
    check_pdf(data)
    created = now()
    digest = hashlib.sha256(data).hexdigest()
    key = f"documents/{uuid.uuid4()}.pdf"
    path = Path(get_settings().storage_dir) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

    doc = Document(
        organization_id=actor.organization_id,
        reference=next_reference(db, actor.organization_id, created.year),
        doc_type=doc_type,
        status=DocStatus.TO_REVIEW,
        filename=(Path(filename).name or "document.pdf")[:255],
        size_bytes=len(data),
        sha256=digest,
        storage_key=key,
        request_id=request.id if request else None,
        uploaded_by_id=actor.id,
        is_synthetic=is_synthetic,
        created_at=created,
        updated_at=created,
    )
    try:
        text = extract_text(data)
        doc.text, doc.page_count = text.text, text.page_count
        doc.ocr_pages, doc.ocr_confidence = text.ocr_pages, text.ocr_confidence
    except TextExtractionError as exc:
        doc.text_error = str(exc)
    db.add(doc)
    db.flush()

    kind = as_doc_type(doc_type.value)
    started = time.perf_counter()
    if doc.text.strip():
        result = _run_extractor(extractor or get_document_extractor(), kind, doc.text, doc.ocr_confidence)
    else:  # rien à lire : le collaborateur saisit les champs en regardant le PDF
        result = ExtractionResult(
            data=validate_fields(kind, {}),
            confidence={f.name: 0.0 for f in FIELDS[kind]},
            provider="aucun (texte illisible)",
        )
    latency = int((time.perf_counter() - started) * 1000)

    db.add(
        Extraction(
            document_id=doc.id,
            version=1,
            source=ExtractionSource.AI,
            provider=result.provider,
            data=result.data,
            confidence=result.confidence,
            created_at=created,
        )
    )
    present = [result.confidence.get(k, 0.0) for k, v in result.data.items() if v is not None]
    db.add(
        AiSuggestion(
            organization_id=doc.organization_id,
            target_type="document",
            target_id=doc.id,
            kind=EXTRACTION_KIND,
            proposal=result.data,
            explanation=" ".join(result.notes) or f"{len(present)} champ(s) lu(s) sur {len(result.data)}.",
            confidence=round(min(present), 2) if present else 0.0,
            provider=result.provider,
            latency_ms=latency,
            decision=Decision.PENDING,
            created_at=created,
        )
    )
    refresh_anomalies(db, doc, result.data)
    if request:
        add_event(db, request, actor, "document_linked", None, None, doc.reference)
    log_action(db, "document.uploaded", "document", doc.id, actor=actor, reference=doc.reference)
    return doc


def _editable(doc: Document) -> None:
    if doc.status != DocStatus.TO_REVIEW:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce document a déjà été validé ou rejeté.")


def correct(db: Session, doc: Document, actor: User, changes: dict[str, Any]) -> Extraction:
    """RD-06 : une correction crée une nouvelle version, l'ancienne reste consultable."""
    _editable(doc)
    current = latest_extraction(db, doc.id)
    assert current is not None
    doc_type = as_doc_type(doc.doc_type.value)
    unknown = set(changes) - {f.name for f in FIELDS[doc_type]}
    if unknown:
        raise _unprocessable(f"Champ(s) inconnu(s) : {', '.join(sorted(unknown))}.")
    try:
        data = validate_fields(doc_type, {**current.data, **changes})
    except ValidationError as exc:
        first = exc.errors()[0]
        raise _unprocessable(f"Valeur invalide pour {first['loc'][0]} : {first['msg']}.") from exc
    changed = [k for k in data if data[k] != current.data.get(k)]
    if not changed:
        return current
    confidence = {**current.confidence, **{k: 1.0 for k in changed}}  # valeur vue par un humain
    version = Extraction(
        document_id=doc.id,
        version=current.version + 1,
        source=ExtractionSource.HUMAN,
        provider="saisie",
        data=data,
        confidence=confidence,
        created_by_id=actor.id,
        created_at=now(),
    )
    db.add(version)
    doc.updated_at = now()
    refresh_anomalies(db, doc, data)
    return version


def blocking(db: Session, doc_id: uuid.UUID) -> list[Anomaly]:
    return list(
        db.scalars(select(Anomaly).where(Anomaly.document_id == doc_id, Anomaly.severity == "BLOCKING"))
    )


def validate(db: Session, doc: Document, actor: User) -> None:
    """RD-07 : validation impossible tant qu'une anomalie bloquante subsiste."""
    _editable(doc)
    if blocks := blocking(db, doc.id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Validation impossible : " + " ".join(a.message for a in blocks),
        )
    current, first = latest_extraction(db, doc.id), first_extraction(db, doc.id)
    assert current is not None and first is not None
    doc.status, doc.decided_by_id, doc.decided_at = DocStatus.VALIDATED, actor.id, now()
    _decide_suggestion(
        db, doc, actor, Decision.ACCEPTED if current.data == first.data else Decision.MODIFIED, current.data
    )
    log_action(
        db,
        "document.validated",
        "document",
        doc.id,
        actor=actor,
        reference=doc.reference,
        version=current.version,
    )


def reject(db: Session, doc: Document, actor: User, reason: str) -> None:
    _editable(doc)
    if not reason.strip():
        raise _unprocessable("Indiquez le motif du rejet.")
    doc.status, doc.decided_by_id, doc.decided_at = DocStatus.REJECTED, actor.id, now()
    doc.rejection_reason = reason.strip()[:1000]
    _decide_suggestion(db, doc, actor, Decision.REJECTED, {"reason": doc.rejection_reason})
    log_action(
        db,
        "document.rejected",
        "document",
        doc.id,
        actor=actor,
        reference=doc.reference,
        reason=doc.rejection_reason,
    )


def _decide_suggestion(
    db: Session, doc: Document, actor: User, decision: Decision, final: dict[str, Any]
) -> None:
    suggestion = suggestion_for(db, doc.id)
    if suggestion is not None:
        suggestion.decision, suggestion.final_value = decision, final
        suggestion.decided_by_id, suggestion.decided_at = actor.id, now()


def link(db: Session, doc: Document, actor: User, request: ServiceRequest | None) -> None:
    """RD-08 : rattacher (ou détacher) un document non rejeté ; tracé dans l'historique de la demande."""
    if doc.status == DocStatus.REJECTED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Un document rejeté ne peut pas être rattaché.")
    previous = db.get(ServiceRequest, doc.request_id) if doc.request_id else None
    if previous and (request is None or previous.id != request.id):
        add_event(db, previous, actor, "document_unlinked", None, doc.reference, None)
    if request and (previous is None or previous.id != request.id):
        add_event(db, request, actor, "document_linked", None, None, doc.reference)
    doc.request_id = request.id if request else None
    doc.updated_at = now()
