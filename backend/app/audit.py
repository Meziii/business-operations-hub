import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def log_action(
    db: Session,
    action: str,
    entity: str,
    entity_id: uuid.UUID | str | None = None,
    actor: User | None = None,
    organization_id: uuid.UUID | None = None,
    **details: Any,
) -> None:
    """Ajoute une ligne au journal d'audit. Le commit reste à la charge de l'appelant."""
    db.add(
        AuditLog(
            organization_id=actor.organization_id if actor else organization_id,
            actor_id=actor.id if actor else None,
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id else None,
            details=details,
        )
    )
