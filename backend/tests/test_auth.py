from sqlalchemy import select

from app.models import AuditLog, User
from app.security import SESSION_COOKIE
from tests.conftest import PASSWORD, login, make_org


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["database"] == "ok"


def test_login_sets_httponly_cookie_and_returns_profile(client, db):
    org = make_org(db)
    agent = org["AGENT"]
    r = client.post("/api/auth/login", json={"email": agent.email.upper(), "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "AGENT"
    assert body["organization_name"] == "Org test"
    assert [t["code"] for t in body["teams"]] == ["SUPPORT"]
    cookie = r.headers["set-cookie"]
    assert SESSION_COOKIE in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie


def test_wrong_password_is_rejected_and_audited(client, db):
    org = make_org(db)
    r = client.post("/api/auth/login", json={"email": org["AGENT"].email, "password": "mauvais"})
    assert r.status_code == 401
    actions = db.scalars(select(AuditLog.action)).all()
    assert actions == ["auth.login_failed"]


def test_unknown_email_gives_same_error(client, db):
    make_org(db)
    r = client.post("/api/auth/login", json={"email": "inconnu@example.com", "password": "x"})
    assert r.status_code == 401
    assert r.json()["detail"] == "E-mail ou mot de passe incorrect."


def test_me_requires_session(client):
    assert client.get("/api/auth/me").status_code == 401


def test_tampered_token_is_rejected(client, db):
    make_org(db)
    client.cookies.set(SESSION_COOKIE, "abc.def.ghi")
    assert client.get("/api/auth/me").status_code == 401


def test_deactivated_user_loses_access(client, db):
    org = make_org(db)
    agent = org["AGENT"]
    login(client, agent)
    user = db.get(User, agent.id)
    user.is_active = False
    db.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_cookie(client, db):
    org = make_org(db)
    login(client, org["AGENT"])
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
