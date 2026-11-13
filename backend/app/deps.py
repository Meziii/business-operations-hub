import uuid
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Role, User
from app.security import SESSION_COOKIE, decode_token

DbSession = Annotated[Session, Depends(get_db)]

_UNAUTHENTICATED = HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentification requise.")


def current_user(request: Request, db: DbSession) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise _UNAUTHENTICATED
    try:
        user_id = uuid.UUID(decode_token(token)["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _UNAUTHENTICATED from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _UNAUTHENTICATED
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_roles(*roles: Role) -> Callable[[User], User]:
    """Dépendance FastAPI : refuse (403) les rôles non autorisés. Le contrôle se fait côté API (NFR-01)."""

    def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Droits insuffisants.")
        return user

    return dependency
