"""Administration : utilisateurs, équipes, journal d'audit, filtrés sur l'organisation de l'appelant."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import log_action
from app.deps import CurrentUser, DbSession, require_roles
from app.models import AuditLog, Role, Team, User, user_teams
from app.schemas import AuditOut, TeamCreate, TeamWithCount, UserCreate, UserOut, UserUpdate
from app.security import hash_password

router = APIRouter(prefix="/api/admin", tags=["admin"])

Admin = Annotated[User, Depends(require_roles(Role.ADMIN))]
AdminOrManager = Annotated[User, Depends(require_roles(Role.ADMIN, Role.MANAGER))]


def _teams(db: Session, org_id: uuid.UUID, ids: list[uuid.UUID]) -> list[Team]:
    teams = list(db.scalars(select(Team).where(Team.organization_id == org_id, Team.id.in_(ids))))
    if len(teams) != len(set(ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Équipe inconnue.")
    return teams


@router.get("/users", response_model=list[UserOut])
def list_users(user: AdminOrManager, db: DbSession) -> list[User]:
    stmt = select(User).where(User.organization_id == user.organization_id).order_by(User.full_name)
    return list(db.scalars(stmt))


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, admin: Admin, db: DbSession) -> User:
    if db.scalar(select(User.id).where(func.lower(User.email) == body.email.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "Cet e-mail est déjà utilisé.")
    new = User(
        organization_id=admin.organization_id,
        email=body.email.lower(),
        full_name=body.full_name,
        role=body.role,
        password_hash=hash_password(body.password),
        teams=_teams(db, admin.organization_id, body.team_ids),
    )
    db.add(new)
    db.flush()
    log_action(db, "user.created", "user", new.id, actor=admin, role=new.role.value)
    db.commit()
    return new


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: uuid.UUID, body: UserUpdate, admin: Admin, db: DbSession) -> User:
    target = db.get(User, user_id)
    if target is None or target.organization_id != admin.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Utilisateur introuvable.")
    if target.id == admin.id and (body.is_active is False or (body.role and body.role != Role.ADMIN)):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Un administrateur ne peut pas se retirer ses droits."
        )

    changes: dict[str, object] = {}
    if body.role is not None and body.role != target.role:
        changes["role"] = [target.role.value, body.role.value]
        target.role = body.role
    if body.is_active is not None and body.is_active != target.is_active:
        changes["is_active"] = [target.is_active, body.is_active]
        target.is_active = body.is_active
    if body.team_ids is not None:
        target.teams = _teams(db, admin.organization_id, body.team_ids)
        changes["teams"] = sorted(t.code for t in target.teams)
    if changes:
        log_action(db, "user.updated", "user", target.id, actor=admin, changes=changes)
    db.commit()
    return target


@router.get("/teams", response_model=list[TeamWithCount])
def list_teams(user: CurrentUser, db: DbSession) -> list[TeamWithCount]:
    count = func.count(user_teams.c.user_id)
    stmt = (
        select(Team, count)
        .outerjoin(user_teams, user_teams.c.team_id == Team.id)
        .where(Team.organization_id == user.organization_id)
        .group_by(Team.id)
        .order_by(Team.name)
    )
    return [TeamWithCount(id=t.id, code=t.code, name=t.name, member_count=n) for t, n in db.execute(stmt)]


@router.post("/teams", response_model=TeamWithCount, status_code=status.HTTP_201_CREATED)
def create_team(body: TeamCreate, admin: Admin, db: DbSession) -> TeamWithCount:
    exists = db.scalar(
        select(Team.id).where(Team.organization_id == admin.organization_id, Team.code == body.code)
    )
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce code d'équipe existe déjà.")
    team = Team(organization_id=admin.organization_id, code=body.code, name=body.name)
    db.add(team)
    db.flush()
    log_action(db, "team.created", "team", team.id, actor=admin, code=team.code)
    db.commit()
    return TeamWithCount(id=team.id, code=team.code, name=team.name, member_count=0)


@router.get("/audit", response_model=list[AuditOut])
def list_audit(admin: Admin, db: DbSession, limit: int = 100) -> list[AuditOut]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.organization_id == admin.organization_id)
        .order_by(AuditLog.id.desc())
        .limit(min(max(limit, 1), 500))
    )
    return [
        AuditOut(
            id=a.id,
            action=a.action,
            entity=a.entity,
            entity_id=a.entity_id,
            actor_email=a.actor.email if a.actor else None,
            details=a.details,
            created_at=a.created_at,
        )
        for a in db.scalars(stmt)
    ]
