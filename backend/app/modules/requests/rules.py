"""Règles de gestion des demandes (docs/03-processes/request-handling.md, RG-01 à RG-12).

Fonctions pures autant que possible : elles sont testées sans passer par l'API.
"""

from datetime import datetime, timedelta
from typing import Literal

from app.models import Priority, Role, ServiceRequest, SlaPolicy, Status, User

OPEN_STATUSES = (
    Status.NEW,
    Status.CLASSIFIED,
    Status.ASSIGNED,
    Status.IN_PROGRESS,
    Status.WAITING_INFO,
)

# RG-02 : transitions déclenchées à la main. NEW → CLASSIFIED et CLASSIFIED ↔ ASSIGNED
# sont automatiques (classement complet, affectation), voir RG-03 et RG-04.
MANUAL_TRANSITIONS: dict[Status, tuple[Status, ...]] = {
    Status.ASSIGNED: (Status.IN_PROGRESS,),
    Status.IN_PROGRESS: (Status.WAITING_INFO, Status.RESOLVED),
    Status.WAITING_INFO: (Status.IN_PROGRESS,),
    Status.RESOLVED: (Status.CLOSED, Status.IN_PROGRESS),
}

# RG-08 : ces passages exigent un commentaire (ce qui manque, ce qui a été fait).
COMMENT_REQUIRED = (Status.WAITING_INFO, Status.RESOLVED)

SlaState = Literal["NONE", "ON_TRACK", "AT_RISK", "BREACHED", "MET"]


def allowed_transitions(status: Status) -> tuple[Status, ...]:
    return MANUAL_TRANSITIONS.get(status, ())


def compute_due_dates(created_at: datetime, sla: SlaPolicy | None) -> tuple[datetime | None, datetime | None]:
    """RG-05 : échéances = création + délais de la priorité, en minutes calendaires."""
    if sla is None:
        return None, None
    return (
        created_at + timedelta(minutes=sla.response_minutes),
        created_at + timedelta(minutes=sla.resolution_minutes),
    )


def sla_state(req: ServiceRequest, now: datetime) -> tuple[SlaState, datetime | None]:
    """État SLA affiché et prochaine échéance à surveiller.

    Une demande résolue est « MET » ou « BREACHED » selon sa date de résolution.
    Une demande ouverte est « AT_RISK » quand il reste moins d'un quart du délai.
    """
    if req.due_resolution_at is None:
        return "NONE", None
    if req.resolved_at is not None:
        return ("MET" if req.resolved_at <= req.due_resolution_at else "BREACHED"), None

    response_late = (
        req.first_response_at is None and req.due_response_at is not None and now > req.due_response_at
    )
    response_missed = (
        req.first_response_at is not None
        and req.due_response_at is not None
        and req.first_response_at > req.due_response_at
    )
    if now > req.due_resolution_at or response_late:
        return "BREACHED", req.due_resolution_at
    next_due = (
        req.due_response_at
        if req.first_response_at is None and req.due_response_at is not None
        else req.due_resolution_at
    )
    total = (next_due - req.created_at).total_seconds()
    remaining = (next_due - now).total_seconds()
    if response_missed or (total > 0 and remaining < total / 4):
        return "AT_RISK", next_due
    return "ON_TRACK", next_due


def is_overdue(req: ServiceRequest, now: datetime) -> bool:
    return req.status in OPEN_STATUSES and sla_state(req, now)[0] == "BREACHED"


def is_classified(req: ServiceRequest) -> bool:
    return req.category_id is not None and req.priority is not None and req.team_id is not None


def team_ids(user: User) -> set[object]:
    return {t.id for t in user.teams}


def can_view(user: User, req: ServiceRequest) -> bool:
    """RG-11 : un collaborateur voit ses équipes, les demandes non routées et les siennes."""
    if req.organization_id != user.organization_id:
        return False
    if user.role != Role.AGENT:
        return True
    return (
        req.team_id is None
        or req.team_id in team_ids(user)
        or req.assignee_id == user.id
        or req.created_by_id == user.id
    )


def can_edit(user: User, req: ServiceRequest) -> bool:
    if user.role == Role.VIEWER or req.status == Status.CLOSED:
        return False
    return can_view(user, req)


PRIORITY_LABELS: dict[Priority, str] = {
    Priority.LOW: "Basse",
    Priority.MEDIUM: "Normale",
    Priority.HIGH: "Haute",
    Priority.CRITICAL: "Critique",
}
