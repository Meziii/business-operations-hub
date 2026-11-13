from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select

from app.audit import log_action
from app.config import get_settings
from app.deps import CurrentUser, DbSession
from app.models import User
from app.schemas import LoginIn, MeOut, UserOut
from app.security import SESSION_COOKIE, create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Vérification factice quand l'e-mail est inconnu : même durée de réponse, pas d'énumération des comptes.
_DUMMY_HASH = hash_password("not-a-real-password")


def _me(user: User) -> MeOut:
    base = UserOut.model_validate(user)
    return MeOut(**base.model_dump(), organization_name=user.organization.name)


@router.post("/login", response_model=MeOut)
def login(body: LoginIn, response: Response, db: DbSession) -> MeOut:
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    valid = verify_password(user.password_hash if user else _DUMMY_HASH, body.password)
    if user is None or not valid or not user.is_active:
        if user is not None:
            log_action(db, "auth.login_failed", "user", user.id, organization_id=user.organization_id)
            db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou mot de passe incorrect.")

    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        create_token(user.id),
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    log_action(db, "auth.login", "user", user.id, actor=user)
    db.commit()
    return _me(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=MeOut)
def me(user: CurrentUser) -> MeOut:
    return _me(user)
