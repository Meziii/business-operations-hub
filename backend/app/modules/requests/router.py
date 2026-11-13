"""Module 1 — API des demandes. Chaque route contrôle les droits côté serveur (NFR-01)."""

import hashlib
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import ColumnElement, Select, and_, func, or_, select
from sqlalchemy.orm import Session

from app.ai import get_triage_provider
from app.ai.evaluate import evaluate
from app.ai.triage import MockTriageProvider
from app.audit import log_action
from app.config import get_settings
from app.deps import CurrentUser, DbSession, require_roles
from app.models import (
    Account,
    AiSuggestion,
    Attachment,
    Category,
    Comment,
    Decision,
    Priority,
    RequestEvent,
    Role,
    ServiceRequest,
    SlaPolicy,
    Status,
    Team,
    User,
)
from app.modules.requests import service
from app.modules.requests.rules import OPEN_STATUSES, allowed_transitions, can_edit, can_view, sla_state
from app.modules.requests.schemas import (
    AttachmentOut,
    CommentIn,
    CommentOut,
    DecisionIn,
    LiveQuality,
    QualityOut,
    ReferenceData,
    RequestCreate,
    RequestDetail,
    RequestPage,
    RequestRow,
    RequestStats,
    RequestUpdate,
    SlaOut,
    SlaUpdate,
    TeamLoad,
    TransitionIn,
)

router = APIRouter(prefix="/api", tags=["requests"])

Writer = Annotated[User, Depends(require_roles(Role.ADMIN, Role.MANAGER, Role.AGENT))]
Manager = Annotated[User, Depends(require_roles(Role.ADMIN, Role.MANAGER))]
Admin = Annotated[User, Depends(require_roles(Role.ADMIN))]

PDF_MAGIC = b"%PDF-"


# --- Accès ------------------------------------------------------------------------------------


def visible[S: Select[Any]](stmt: S, user: User) -> S:
    """Filtre SQL équivalent à rules.can_view (RG-11).

    Générique sur le type de requête : SQLAlchemy 2.0 et 2.1 ne paramètrent pas `Select` de la même façon.
    """
    stmt = stmt.where(ServiceRequest.organization_id == user.organization_id)
    if user.role == Role.AGENT:
        stmt = stmt.where(
            or_(
                ServiceRequest.team_id.is_(None),
                ServiceRequest.team_id.in_([t.id for t in user.teams]),
                ServiceRequest.assignee_id == user.id,
                ServiceRequest.created_by_id == user.id,
            )
        )
    return stmt


def get_request(db: Session, user: User, request_id: uuid.UUID, write: bool = False) -> ServiceRequest:
    req = db.get(ServiceRequest, request_id)
    if req is None or not can_view(user, req):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Demande introuvable.")
    if write and not can_edit(user, req):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Vous ne pouvez pas modifier cette demande.")
    return req


def _overdue_clause() -> ColumnElement[bool]:
    now = service.now()
    return and_(
        ServiceRequest.status.in_(OPEN_STATUSES),
        or_(
            ServiceRequest.due_resolution_at < now,
            and_(ServiceRequest.first_response_at.is_(None), ServiceRequest.due_response_at < now),
        ),
    )


# --- Sérialisation ----------------------------------------------------------------------------


def to_row(req: ServiceRequest) -> RequestRow:
    state, next_due = sla_state(req, service.now())
    return RequestRow(
        id=req.id,
        reference=req.reference,
        title=req.title,
        status=req.status,
        priority=req.priority,
        channel=req.channel,
        account={"id": req.account.id, "name": req.account.name},
        category={"id": req.category.id, "name": req.category.name} if req.category else None,
        team=req.team,
        assignee=req.assignee,
        created_at=req.created_at,
        due_response_at=req.due_response_at,
        due_resolution_at=req.due_resolution_at,
        sla_state=state,
        sla_next_due=next_due,
    )


def to_detail(db: Session, req: ServiceRequest, user: User) -> RequestDetail:
    comments = db.scalars(select(Comment).where(Comment.request_id == req.id).order_by(Comment.created_at))
    attachments = db.scalars(
        select(Attachment).where(Attachment.request_id == req.id).order_by(Attachment.created_at)
    )
    events = db.scalars(
        select(RequestEvent).where(RequestEvent.request_id == req.id).order_by(RequestEvent.id)
    )
    editable = can_edit(user, req)
    return RequestDetail(
        **to_row(req).model_dump(),
        description=req.description,
        account_tier=req.account.tier,
        created_by=req.created_by,
        first_response_at=req.first_response_at,
        resolved_at=req.resolved_at,
        closed_at=req.closed_at,
        updated_at=req.updated_at,
        can_edit=editable,
        allowed_transitions=list(allowed_transitions(req.status)) if editable else [],
        comments=list(comments),
        attachments=list(attachments),
        events=list(events),
        suggestion=service.latest_suggestion(db, req.id),
    )


# --- Référentiel ------------------------------------------------------------------------------


@router.get("/reference", response_model=ReferenceData)
def reference(user: CurrentUser, db: DbSession) -> ReferenceData:
    org = user.organization_id
    assignees = db.scalars(
        select(User)
        .where(User.organization_id == org, User.is_active.is_(True), User.role != Role.VIEWER)
        .order_by(User.full_name)
    )
    return ReferenceData(
        accounts=list(
            db.scalars(select(Account).where(Account.organization_id == org).order_by(Account.name))
        ),
        categories=list(
            db.scalars(select(Category).where(Category.organization_id == org).order_by(Category.name))
        ),
        teams=list(db.scalars(select(Team).where(Team.organization_id == org).order_by(Team.name))),
        sla=sorted(
            db.scalars(select(SlaPolicy).where(SlaPolicy.organization_id == org)),
            key=lambda s: list(Priority).index(s.priority),
        ),
        assignees=[
            {"id": u.id, "full_name": u.full_name, "team_ids": [t.id for t in u.teams]}
            for u in assignees
            if u.teams
        ],
        ai_provider=get_triage_provider().name,
    )


@router.put("/reference/sla/{priority}", response_model=SlaOut)
def update_sla(priority: Priority, body: SlaUpdate, admin: Admin, db: DbSession) -> SlaPolicy:
    """US-108 (partiel) : l'administrateur ajuste les délais. Les échéances existantes ne bougent pas."""
    if body.resolution_minutes < body.response_minutes:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Le délai de résolution doit couvrir la prise en charge."
        )
    sla = db.scalar(
        select(SlaPolicy).where(
            SlaPolicy.organization_id == admin.organization_id, SlaPolicy.priority == priority
        )
    )
    if sla is None:
        sla = SlaPolicy(
            organization_id=admin.organization_id, priority=priority, response_minutes=1, resolution_minutes=1
        )
        db.add(sla)
    before = [sla.response_minutes, sla.resolution_minutes]
    sla.response_minutes, sla.resolution_minutes = body.response_minutes, body.resolution_minutes
    db.flush()
    log_action(
        db,
        "sla.updated",
        "sla_policy",
        sla.id,
        actor=admin,
        priority=priority.value,
        before=before,
        after=[body.response_minutes, body.resolution_minutes],
    )
    db.commit()
    return sla


# --- Demandes ---------------------------------------------------------------------------------


@router.get("/requests", response_model=RequestPage)
def list_requests(
    user: CurrentUser,
    db: DbSession,
    status_: Annotated[list[Status] | None, Query(alias="status")] = None,
    priority: Annotated[list[Priority] | None, Query()] = None,
    category_id: uuid.UUID | None = None,
    team_id: uuid.UUID | None = None,
    assignee: str | None = Query(default=None, description="me, none ou un identifiant"),
    overdue: bool = False,
    open_only: bool = False,
    q: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> RequestPage:
    stmt = visible(select(ServiceRequest), user)
    if status_:
        stmt = stmt.where(ServiceRequest.status.in_(status_))
    if open_only:
        stmt = stmt.where(ServiceRequest.status.in_(OPEN_STATUSES))
    if priority:
        stmt = stmt.where(ServiceRequest.priority.in_(priority))
    if category_id:
        stmt = stmt.where(ServiceRequest.category_id == category_id)
    if team_id:
        stmt = stmt.where(ServiceRequest.team_id == team_id)
    if assignee == "me":
        stmt = stmt.where(ServiceRequest.assignee_id == user.id)
    elif assignee == "none":
        stmt = stmt.where(ServiceRequest.assignee_id.is_(None))
    elif assignee:
        try:
            stmt = stmt.where(ServiceRequest.assignee_id == uuid.UUID(assignee))
        except ValueError:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Filtre d'affectation invalide."
            ) from None
    if overdue:
        stmt = stmt.where(_overdue_clause())
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.join(Account).where(
            or_(
                ServiceRequest.reference.ilike(pattern),
                ServiceRequest.title.ilike(pattern),
                ServiceRequest.description.ilike(pattern),
                Account.name.ilike(pattern),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    # Tri : ouvertes d'abord, puis échéance la plus proche, puis les plus récentes.
    is_closed = ServiceRequest.status.in_([Status.RESOLVED, Status.CLOSED])
    rows = db.scalars(
        stmt.order_by(
            is_closed,
            ServiceRequest.due_resolution_at.asc().nulls_first(),
            ServiceRequest.created_at.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return RequestPage(items=[to_row(r) for r in rows], total=total, page=page, page_size=page_size)


@router.post("/requests", response_model=RequestDetail, status_code=status.HTTP_201_CREATED)
def create_request(body: RequestCreate, user: Writer, db: DbSession) -> RequestDetail:
    req = service.create_request(db, user, body.account_id, body.channel, body.title, body.description)
    service.suggest_triage(db, req)
    db.commit()
    db.refresh(req)
    return to_detail(db, req, user)


@router.get("/requests/stats", response_model=RequestStats)
def stats(user: CurrentUser, db: DbSession) -> RequestStats:
    base = visible(select(ServiceRequest), user).subquery()
    by_status = {s.value: 0 for s in Status}
    for st, n in db.execute(select(base.c.status, func.count()).group_by(base.c.status)):
        by_status[str(st)] = n
    open_count = sum(by_status[s.value] for s in OPEN_STATUSES)
    overdue = (
        db.scalar(
            select(func.count()).select_from(
                visible(select(ServiceRequest), user).where(_overdue_clause()).subquery()
            )
        )
        or 0
    )
    week_ago = service.now() - timedelta(days=7)
    resolved_recent = (
        db.scalar(
            select(func.count()).select_from(
                visible(select(ServiceRequest), user).where(ServiceRequest.resolved_at >= week_ago).subquery()
            )
        )
        or 0
    )

    teams = list(
        db.scalars(select(Team).where(Team.organization_id == user.organization_id).order_by(Team.name))
    )
    if user.role == Role.AGENT:
        mine = {t.id for t in user.teams}
        teams = [t for t in teams if t.id in mine]

    def count(stmt: Select[Any]) -> int:
        return db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    loads = []
    for team in teams:
        team_open = visible(select(ServiceRequest), user).where(
            ServiceRequest.team_id == team.id, ServiceRequest.status.in_(OPEN_STATUSES)
        )
        loads.append(
            TeamLoad(
                team=team,
                open=count(team_open),
                overdue=count(team_open.where(_overdue_clause())),
                unassigned=count(team_open.where(ServiceRequest.assignee_id.is_(None))),
            )
        )

    decisions = {d.value: 0 for d in Decision}
    for d, n in db.execute(
        select(AiSuggestion.decision, func.count())
        .where(AiSuggestion.organization_id == user.organization_id)
        .group_by(AiSuggestion.decision)
    ):
        decisions[str(d)] = n

    return RequestStats(
        open=open_count,
        overdue=overdue,
        to_classify=by_status[Status.NEW.value],
        waiting_info=by_status[Status.WAITING_INFO.value],
        resolved_last_7_days=resolved_recent,
        by_status=by_status,
        by_team=loads,
        ai_decisions=decisions,
    )


@router.get("/requests/{request_id}", response_model=RequestDetail)
def get_detail(request_id: uuid.UUID, user: CurrentUser, db: DbSession) -> RequestDetail:
    return to_detail(db, get_request(db, user, request_id), user)


@router.patch("/requests/{request_id}", response_model=RequestDetail)
def update_request(request_id: uuid.UUID, body: RequestUpdate, user: Writer, db: DbSession) -> RequestDetail:
    req = get_request(db, user, request_id, write=True)
    service.update_fields(db, req, user, body.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(req)
    return to_detail(db, req, user)


@router.post("/requests/{request_id}/transition", response_model=RequestDetail)
def change_status(request_id: uuid.UUID, body: TransitionIn, user: Writer, db: DbSession) -> RequestDetail:
    req = get_request(db, user, request_id, write=True)
    service.transition(db, req, user, body.status, body.comment)
    db.commit()
    db.refresh(req)
    return to_detail(db, req, user)


@router.post(
    "/requests/{request_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED
)
def add_comment(request_id: uuid.UUID, body: CommentIn, user: Writer, db: DbSession) -> Comment:
    req = get_request(db, user, request_id, write=True)
    comment = Comment(request_id=req.id, author_id=user.id, body=body.body.strip())
    db.add(comment)
    service.add_event(db, req, user, "comment_added")
    db.commit()
    db.refresh(comment)
    return comment


@router.post(
    "/requests/{request_id}/attachments", response_model=AttachmentOut, status_code=status.HTTP_201_CREATED
)
async def upload_attachment(
    request_id: uuid.UUID, file: UploadFile, user: Writer, db: DbSession
) -> Attachment:
    """NFR-03 : PDF uniquement, vérifié sur le contenu, taille plafonnée."""
    req = get_request(db, user, request_id, write=True)
    settings = get_settings()
    limit = settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Fichier trop volumineux ({settings.max_upload_mb} Mo maximum).",
        )
    if not data.startswith(PDF_MAGIC):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Seuls les fichiers PDF sont acceptés.")
    digest = hashlib.sha256(data).hexdigest()
    key = f"{req.organization_id}/{uuid.uuid4()}.pdf"
    path = Path(settings.storage_dir) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    name = Path(file.filename or "document.pdf").name[:255] or "document.pdf"
    att = Attachment(
        request_id=req.id,
        uploaded_by_id=user.id,
        filename=name,
        mime_type="application/pdf",
        size_bytes=len(data),
        sha256=digest,
        storage_key=key,
    )
    db.add(att)
    service.add_event(db, req, user, "attachment_added", None, None, name)
    db.commit()
    db.refresh(att)
    return att


@router.get("/requests/{request_id}/attachments/{attachment_id}")
def download_attachment(
    request_id: uuid.UUID, attachment_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> FileResponse:
    req = get_request(db, user, request_id)
    att = db.get(Attachment, attachment_id)
    if att is None or att.request_id != req.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pièce jointe introuvable.")
    path = Path(get_settings().storage_dir) / att.storage_key
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fichier absent du stockage.")
    return FileResponse(path, media_type=att.mime_type, filename=att.filename)


# --- IA ---------------------------------------------------------------------------------------


@router.post("/requests/{request_id}/suggestion", response_model=RequestDetail)
def regenerate_suggestion(request_id: uuid.UUID, user: Writer, db: DbSession) -> RequestDetail:
    req = get_request(db, user, request_id, write=True)
    if req.status != Status.NEW:
        raise HTTPException(status.HTTP_409_CONFLICT, "La demande est déjà classée.")
    current = service.latest_suggestion(db, req.id)
    if current is not None and current.decision == Decision.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, "Une suggestion attend déjà une décision.")
    service.suggest_triage(db, req)
    db.commit()
    db.refresh(req)
    return to_detail(db, req, user)


@router.post("/suggestions/{suggestion_id}/decision", response_model=RequestDetail)
def decide_suggestion(
    suggestion_id: uuid.UUID, body: DecisionIn, user: Writer, db: DbSession
) -> RequestDetail:
    suggestion = db.get(AiSuggestion, suggestion_id)
    if suggestion is None or suggestion.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Suggestion introuvable.")
    req = get_request(db, user, suggestion.target_id, write=True)
    if body.action == "modify" and not (body.category_id or body.priority or body.team_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Indiquez au moins une valeur corrigée.")
    service.decide(
        db, suggestion, req, user, body.action, body.category_id, body.priority, body.team_id, body.reason
    )
    db.commit()
    db.refresh(req)
    return to_detail(db, req, user)


@router.get("/ai/triage/quality", response_model=QualityOut)
def triage_quality(user: Manager, db: DbSession) -> QualityOut:
    """US-203 : exactitude sur le jeu de test étiqueté + décisions réelles des collaborateurs."""
    offline = evaluate(MockTriageProvider(), split="test")
    decided = list(
        db.scalars(
            select(AiSuggestion).where(
                AiSuggestion.organization_id == user.organization_id,
                AiSuggestion.decision != Decision.PENDING,
            )
        )
    )
    applied = [s for s in decided if s.decision != Decision.REJECTED and s.final_value]
    kept = {
        field: round(
            sum(1 for s in applied if s.final_value and s.final_value.get(field) == s.proposal.get(field))
            / len(applied),
            3,
        )
        if applied
        else 0.0
        for field in ("category_id", "priority", "team_id")
    }
    return QualityOut(
        offline=offline,
        dev_all_three_correct=evaluate(MockTriageProvider(), split="dev").all_three_correct,
        live=LiveQuality(
            decided=len(decided),
            accepted=sum(1 for s in decided if s.decision == Decision.ACCEPTED),
            modified=sum(1 for s in decided if s.decision == Decision.MODIFIED),
            rejected=sum(1 for s in decided if s.decision == Decision.REJECTED),
            field_kept=kept,
        ),
    )
