import pytest
from sqlalchemy import select

from app.models import AuditLog
from tests.conftest import login, make_org

NEW_USER = {
    "email": "nouveau@org.example.com",
    "full_name": "Nouvel Agent",
    "role": "AGENT",
    "password": "Un-mot-de-passe-long",
}


@pytest.mark.parametrize(
    ("role", "expected"), [("ADMIN", 200), ("MANAGER", 200), ("AGENT", 403), ("VIEWER", 403)]
)
def test_list_users_permissions(client, db, role, expected):
    org = make_org(db)
    login(client, org[role])
    assert client.get("/api/admin/users").status_code == expected


@pytest.mark.parametrize("role", ["MANAGER", "AGENT", "VIEWER"])
def test_only_admin_creates_users(client, db, role):
    org = make_org(db)
    login(client, org[role])
    assert client.post("/api/admin/users", json=NEW_USER).status_code == 403


def test_admin_creates_user_with_team_and_audit(client, db):
    org = make_org(db)
    login(client, org["ADMIN"])
    r = client.post("/api/admin/users", json={**NEW_USER, "team_ids": [str(org["team"].id)]})
    assert r.status_code == 201
    assert [t["code"] for t in r.json()["teams"]] == ["SUPPORT"]
    assert "user.created" in db.scalars(select(AuditLog.action)).all()
    assert client.post("/api/admin/users", json=NEW_USER).status_code == 409


def test_short_password_rejected(client, db):
    org = make_org(db)
    login(client, org["ADMIN"])
    assert client.post("/api/admin/users", json={**NEW_USER, "password": "court"}).status_code == 422


def test_admin_cannot_remove_own_rights(client, db):
    org = make_org(db)
    admin = org["ADMIN"]
    login(client, admin)
    assert client.patch(f"/api/admin/users/{admin.id}", json={"is_active": False}).status_code == 400
    assert client.patch(f"/api/admin/users/{admin.id}", json={"role": "AGENT"}).status_code == 400


def test_role_change_is_audited_with_before_after(client, db):
    org = make_org(db)
    login(client, org["ADMIN"])
    r = client.patch(f"/api/admin/users/{org['AGENT'].id}", json={"role": "MANAGER"})
    assert r.status_code == 200 and r.json()["role"] == "MANAGER"
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "user.updated"))
    assert entry.details["changes"]["role"] == ["AGENT", "MANAGER"]


def test_organizations_are_isolated(client, db):
    a = make_org(db, "Org A")
    b = make_org(db, "Org B")
    login(client, b["ADMIN"])
    emails = {u["email"] for u in client.get("/api/admin/users").json()}
    assert a["AGENT"].email not in emails
    assert client.patch(f"/api/admin/users/{a['AGENT'].id}", json={"role": "VIEWER"}).status_code == 404
    r = client.post("/api/admin/users", json={**NEW_USER, "team_ids": [str(a["team"].id)]})
    assert r.status_code == 422


def test_teams_list_counts_members(client, db):
    org = make_org(db)
    login(client, org["VIEWER"])
    teams = client.get("/api/admin/teams").json()
    assert teams == [{"id": str(org["team"].id), "code": "SUPPORT", "name": "Support", "member_count": 1}]


def test_audit_visible_to_admin_only(client, db):
    org = make_org(db)
    login(client, org["MANAGER"])
    assert client.get("/api/admin/audit").status_code == 403
    login(client, org["ADMIN"])
    actions = [a["action"] for a in client.get("/api/admin/audit").json()]
    assert actions[:2] == ["auth.login", "auth.login"]


def test_only_admin_creates_teams(client, db):
    org = make_org(db)
    body = {"code": "SAV", "name": "Service après-vente"}
    login(client, org["MANAGER"])
    assert client.post("/api/admin/teams", json=body).status_code == 403
    login(client, org["ADMIN"])
    assert client.post("/api/admin/teams", json=body).status_code == 201
    assert client.post("/api/admin/teams", json=body).status_code == 409
    assert client.post("/api/admin/teams", json={"code": "bad code", "name": "x"}).status_code == 422
