"""Opérations sur les demandes : création, modifications historisées, transitions, suggestions IA.

Le router contrôle les droits ; ce module applique les règles de gestion et écrit l'historique.
Le commit reste à la charge de l'appelant.
"""

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import get_triage_provider
from app.ai.triage import (
    CategoryOption,
    MockTriageProvider,
    TeamOption,
    TriageError,
    TriageInput,
    TriageProposal,
    TriageProvider,
)
from app.audit import log_action
from app.models import (
    Account,
    AiSuggestion,
    Category,
    Channel,
    Comment,
    Decision,
    Organization,
    Priority,
    RequestEvent,
    ServiceRequest,
    SlaPolicy,
    Status,
    Team,
    User,
)
from app.modules.requests.rules import (
    COMMENT_REQUIRED,
    allowed_transitions,
    compute_due_dates,
    is_classified,
)

TRIAGE_KIND = "REQUEST_TRIAGE"


_clock: ContextVar[datetime | None] = ContextVar("clock", default=None)


def now() -> datetime:
    """Heure courante. Le seed la fige pour reconstituer un historique daté (voir frozen_clock)."""
    return _clock.get() or datetime.now(UTC)


@contextmanager
def frozen_clock(at: datetime) -> Iterator[None]:
    token = _clock.set(at)
    try:
        yield
    finally:
        _clock.reset(token)


def _unprocessable(message: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, message)


def add_event(
    db: Session,
    req: ServiceRequest,
    actor: User | None,
    event_type: str,
    field: str | None = None,
    old: object = None,
    new: object = None,
) -> None:
    def fmt(v: object) -> str | None:
        if v is None:
            return None
        return str(getattr(v, "value", v))[:300]

    event = RequestEvent(
        request_id=req.id,
        actor_id=actor.id if actor else None,
        event_type=event_type,
        field=field,
        old_value=fmt(old),
        new_value=fmt(new),
        created_at=now(),
    )
    db.add(event)


def next_reference(db: Session, org_id: uuid.UUID, year: int) -> str:
    """RG-01 : DEM-AAAA-NNNNN, séquentiel par organisation et par année.

    Verrou sur la ligne de l'organisation pour éviter deux références identiques en parallèle.
    """
    db.execute(select(Organization.id).where(Organization.id == org_id).with_for_update())
    prefix = f"DEM-{year}-"
    last = db.scalar(
        select(func.max(ServiceRequest.reference)).where(
            ServiceRequest.organization_id == org_id, ServiceRequest.reference.like(f"{prefix}%")
        )
    )
    number = int(last.rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}{number:05d}"


def sla_for(db: Session, org_id: uuid.UUID, priority: Priority | None) -> SlaPolicy | None:
    if priority is None:
        return None
    return db.scalar(
        select(SlaPolicy).where(SlaPolicy.organization_id == org_id, SlaPolicy.priority == priority)
    )


def refresh_due_dates(db: Session, req: ServiceRequest) -> None:
    req.due_response_at, req.due_resolution_at = compute_due_dates(
        req.created_at, sla_for(db, req.organization_id, req.priority)
    )


def org_entity[T: (Account, Category, Team, User)](
    db: Session, model: type[T], org_id: uuid.UUID, entity_id: uuid.UUID, label: str
) -> T:
    entity = db.get(model, entity_id)
    if entity is None or entity.organization_id != org_id:
        raise _unprocessable(f"{label} inconnu(e).")
    return entity


def create_request(
    db: Session,
    actor: User,
    account_id: uuid.UUID,
    channel: Channel,
    title: str,
    description: str,
    is_synthetic: bool = False,
) -> ServiceRequest:
    account = org_entity(db, Account, actor.organization_id, account_id, "Client ou partenaire")
    created = now()
    req = ServiceRequest(
        organization_id=actor.organization_id,
        reference=next_reference(db, actor.organization_id, created.year),
        title=title.strip(),
        description=description.strip(),
        channel=channel,
        status=Status.NEW,
        account_id=account.id,
        created_by_id=actor.id,
        is_synthetic=is_synthetic,
        created_at=created,
        updated_at=created,
    )
    db.add(req)
    db.flush()
    add_event(db, req, actor, "created", "status", None, Status.NEW)
    return req


def _set(db: Session, req: ServiceRequest, actor: User, field: str, value: object, label: object) -> bool:
    old = getattr(req, field)
    if old == value:
        return False
    old_label = _label(db, field, old)
    setattr(req, field, value)
    add_event(db, req, actor, "field_changed", field, old_label, label)
    return True


def _label(db: Session, field: str, value: object) -> object:
    if value is None:
        return None
    if field == "category_id":
        cat = db.get(Category, value)
        return cat.name if cat else value
    if field == "team_id":
        team = db.get(Team, value)
        return team.name if team else value
    if field == "assignee_id":
        user = db.get(User, value)
        return user.full_name if user else value
    return value


def _transition(db: Session, req: ServiceRequest, actor: User, to: Status) -> None:
    add_event(db, req, actor, "status_changed", "status", req.status, to)
    req.status = to


def update_fields(db: Session, req: ServiceRequest, actor: User, changes: dict[str, Any]) -> None:
    """Applique des modifications et les transitions automatiques qui en découlent (RG-03, RG-04)."""
    org = req.organization_id
    if "title" in changes and changes["title"]:
        _set(db, req, actor, "title", changes["title"].strip(), changes["title"].strip())
    if "description" in changes and changes["description"]:
        _set(db, req, actor, "description", changes["description"].strip(), "(texte modifié)")
    if "category_id" in changes:
        cid = changes["category_id"]
        cat = org_entity(db, Category, org, cid, "Catégorie") if cid else None
        _set(db, req, actor, "category_id", cid, cat.name if cat else None)
    if "priority" in changes and _set(db, req, actor, "priority", changes["priority"], changes["priority"]):
        refresh_due_dates(db, req)
    if "team_id" in changes:
        tid = changes["team_id"]
        team = org_entity(db, Team, org, tid, "Équipe") if tid else None
        changed = _set(db, req, actor, "team_id", tid, team.name if team else None)
        if changed and req.assignee_id and "assignee_id" not in changes:
            assignee = db.get(User, req.assignee_id)
            if assignee is None or team is None or team not in assignee.teams:
                changes = {**changes, "assignee_id": None}  # RG-04 : l'affecté doit être dans l'équipe
    if "assignee_id" in changes:
        uid = changes["assignee_id"]
        if uid:
            user = org_entity(db, User, org, uid, "Collaborateur")
            if not user.is_active or req.team_id is None or req.team_id not in {t.id for t in user.teams}:
                raise _unprocessable(
                    "La personne affectée doit être active et membre de l'équipe de la demande."
                )
            _set(db, req, actor, "assignee_id", uid, user.full_name)
        else:
            _set(db, req, actor, "assignee_id", None, None)

    # Transitions automatiques
    if req.status == Status.NEW and is_classified(req):
        _transition(db, req, actor, Status.CLASSIFIED)
    if req.status == Status.CLASSIFIED and req.assignee_id:
        _transition(db, req, actor, Status.ASSIGNED)
    if req.status == Status.ASSIGNED and not req.assignee_id:
        _transition(db, req, actor, Status.CLASSIFIED)
    if req.status != Status.NEW and not is_classified(req):
        raise _unprocessable("Une demande classée doit garder sa catégorie, sa priorité et son équipe.")
    if req.status in (Status.IN_PROGRESS, Status.WAITING_INFO, Status.RESOLVED) and not req.assignee_id:
        raise _unprocessable("Une demande prise en charge doit rester affectée à quelqu'un de l'équipe.")


def transition(db: Session, req: ServiceRequest, actor: User, to: Status, comment: str | None) -> None:
    if to not in allowed_transitions(req.status):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Passage de {req.status.value} à {to.value} non autorisé."
        )
    if to in COMMENT_REQUIRED and not (comment and comment.strip()):
        raise _unprocessable("Un commentaire est obligatoire pour ce changement de statut.")
    when = now()
    if comment and comment.strip():
        db.add(Comment(request_id=req.id, author_id=actor.id, body=comment.strip(), created_at=when))
        add_event(db, req, actor, "comment_added")
    add_event(db, req, actor, "status_changed", "status", req.status, to)
    if to == Status.IN_PROGRESS and req.first_response_at is None:
        req.first_response_at = when  # RG-06 : prise en charge
    if to == Status.RESOLVED:
        req.resolved_at = when
    if to == Status.IN_PROGRESS and req.status == Status.RESOLVED:
        req.resolved_at = None  # RG-07 : réouverture
    if to == Status.CLOSED:
        req.closed_at = when
    req.status = to


# --- Suggestions IA -------------------------------------------------------------------------


def _options(db: Session, org_id: uuid.UUID) -> tuple[list[CategoryOption], list[TeamOption]]:
    teams = list(db.scalars(select(Team).where(Team.organization_id == org_id).order_by(Team.code)))
    codes = {t.id: t.code for t in teams}
    cats = db.scalars(select(Category).where(Category.organization_id == org_id).order_by(Category.code))
    return (
        [
            CategoryOption(c.code, c.name, c.description, codes.get(c.default_team_id))  # type: ignore[arg-type]
            for c in cats
        ],
        [TeamOption(t.code, t.name) for t in teams],
    )


def _validated(proposal: TriageProposal, cats: list[CategoryOption], teams: list[TeamOption]) -> None:
    if proposal.category_code not in {c.code for c in cats}:
        raise TriageError(f"Catégorie inconnue proposée : {proposal.category_code}")
    if proposal.team_code not in {t.code for t in teams}:
        raise TriageError(f"Équipe inconnue proposée : {proposal.team_code}")


def suggest_triage(
    db: Session, req: ServiceRequest, provider: TriageProvider | None = None
) -> AiSuggestion | None:
    """Produit une suggestion pour une demande NEW. Repli sur les règles si le fournisseur échoue."""
    cats, teams = _options(db, req.organization_id)
    if not cats or not teams:
        return None
    account = db.get(Account, req.account_id)
    item = TriageInput(req.title, req.description, req.channel.value, account.tier.value if account else "")
    provider = provider or get_triage_provider()
    started = time.perf_counter()
    try:
        proposal = provider.suggest(item, cats, teams)
        _validated(proposal, cats, teams)
        provider_name = provider.name
    except TriageError as exc:
        fallback = MockTriageProvider()
        proposal = fallback.suggest(item, cats, teams)
        proposal.explanation = f"[Repli sur les règles : {exc}] {proposal.explanation}"
        provider_name = f"{fallback.name} (repli)"
    latency = int((time.perf_counter() - started) * 1000)

    by_code_cat = {
        c.code: c.id
        for c in db.scalars(select(Category).where(Category.organization_id == req.organization_id))
    }
    by_code_team = {
        t.code: t.id for t in db.scalars(select(Team).where(Team.organization_id == req.organization_id))
    }
    suggestion = AiSuggestion(
        organization_id=req.organization_id,
        target_type="request",
        target_id=req.id,
        kind=TRIAGE_KIND,
        proposal={
            "category_id": str(by_code_cat[proposal.category_code]),
            "category_code": proposal.category_code,
            "priority": proposal.priority,
            "team_id": str(by_code_team[proposal.team_code]),
            "team_code": proposal.team_code,
            "field_confidence": proposal.confidence,
        },
        explanation=proposal.explanation,
        confidence=proposal.overall_confidence,
        provider=provider_name,
        latency_ms=latency,
        decision=Decision.PENDING,
        created_at=now(),
    )
    db.add(suggestion)
    db.flush()
    add_event(db, req, None, "ai_suggested", None, None, f"{proposal.category_code} / {proposal.priority}")
    return suggestion


def latest_suggestion(db: Session, req_id: uuid.UUID) -> AiSuggestion | None:
    return db.scalar(
        select(AiSuggestion)
        .where(AiSuggestion.target_id == req_id, AiSuggestion.kind == TRIAGE_KIND)
        .order_by(AiSuggestion.created_at.desc())
        .limit(1)
    )


def decide(
    db: Session,
    suggestion: AiSuggestion,
    req: ServiceRequest,
    actor: User,
    action: str,
    category_id: uuid.UUID | None,
    priority: Priority | None,
    team_id: uuid.UUID | None,
    reason: str | None,
) -> None:
    """RG-10 : accepter ou modifier applique le classement ; rejeter ne change rien à la demande."""
    if suggestion.decision != Decision.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cette suggestion a déjà été traitée.")
    if req.status != Status.NEW:
        raise HTTPException(status.HTTP_409_CONFLICT, "La demande est déjà classée.")
    p = suggestion.proposal
    if action == "reject":
        suggestion.decision = Decision.REJECTED
        suggestion.final_value = {"reason": reason} if reason else None
    else:
        final = {
            "category_id": str(category_id) if action == "modify" and category_id else p["category_id"],
            "priority": (priority.value if action == "modify" and priority else p["priority"]),
            "team_id": str(team_id) if action == "modify" and team_id else p["team_id"],
        }
        same = all(final[k] == p[k] for k in ("category_id", "priority", "team_id"))
        suggestion.decision = Decision.ACCEPTED if same else Decision.MODIFIED
        suggestion.final_value = final
        update_fields(
            db,
            req,
            actor,
            {
                "category_id": uuid.UUID(final["category_id"]),
                "priority": Priority(final["priority"]),
                "team_id": uuid.UUID(final["team_id"]),
            },
        )
    suggestion.decided_by_id = actor.id
    suggestion.decided_at = now()
    add_event(db, req, actor, "ai_decision", None, None, suggestion.decision)
    log_action(
        db,
        "ai_suggestion.decided",
        "ai_suggestion",
        suggestion.id,
        actor=actor,
        decision=suggestion.decision.value,
        request=req.reference,
    )
