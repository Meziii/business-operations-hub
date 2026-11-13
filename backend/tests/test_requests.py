"""Module 1 — demandes : création, tri assisté, cycle de vie, SLA, droits, historique, pièces jointes."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.ai.triage import TriageError, TriageProposal
from app.config import get_settings
from app.demo_catalog import CATEGORIES, SLA
from app.models import (
    Account,
    AccountTier,
    AccountType,
    AuditLog,
    Category,
    Channel,
    Priority,
    RequestEvent,
    Role,
    ServiceRequest,
    SlaPolicy,
    Team,
    User,
)
from app.modules.requests import service
from app.modules.requests.rules import sla_state
from tests.conftest import _HASH, login, make_org

DELIVERY_TEXT = {
    "channel": "EMAIL",
    "title": "Colis non reçu",
    "description": "Notre commande devait être livrée hier mais le colis n'est jamais arrivé chez nous.",
}


def setup_module_data(db, org):
    """Catégories, SLA, deux comptes clients, une équipe après-vente avec son agent."""
    org_id = org["org"].id
    teams = {"SUPPORT": org["team"]}
    for code in ("AFTER_SALES", "SALES", "ADMIN_FIN"):
        teams[code] = Team(organization_id=org_id, code=code, name=code.title())
        db.add(teams[code])
    db.flush()
    for code, name, desc, team in CATEGORIES:
        db.add(
            Category(
                organization_id=org_id, code=code, name=name, description=desc, default_team_id=teams[team].id
            )
        )
    for prio, (resp, reso) in SLA.items():
        db.add(
            SlaPolicy(organization_id=org_id, priority=prio, response_minutes=resp, resolution_minutes=reso)
        )
    std = Account(
        organization_id=org_id, name="Client Standard", type=AccountType.CUSTOMER, tier=AccountTier.STANDARD
    )
    premium = Account(
        organization_id=org_id, name="Client Premium", type=AccountType.CUSTOMER, tier=AccountTier.PREMIUM
    )
    sav_agent = User(
        organization_id=org_id,
        email=f"sav@{org_id}.example.com",
        full_name="Agent SAV",
        role=Role.AGENT,
        password_hash=_HASH,
        teams=[teams["AFTER_SALES"]],
    )
    db.add_all([std, premium, sav_agent])
    db.commit()
    return {**org, "teams": teams, "account": std, "premium": premium, "sav_agent": sav_agent}


@pytest.fixture
def ctx(db):
    return setup_module_data(db, make_org(db))


def create(client, ctx, **overrides):
    body = {**DELIVERY_TEXT, "account_id": str(ctx["account"].id), **overrides}
    r = client.post("/api/requests", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def accept(client, detail):
    r = client.post(f"/api/suggestions/{detail['suggestion']['id']}/decision", json={"action": "accept"})
    assert r.status_code == 200, r.text
    return r.json()


def assign(client, detail, user):
    r = client.patch(f"/api/requests/{detail['id']}", json={"assignee_id": str(user.id)})
    assert r.status_code == 200, r.text
    return r.json()


def move(client, detail, status, comment=None):
    return client.post(
        f"/api/requests/{detail['id']}/transition", json={"status": status, "comment": comment}
    )


# --- Création et suggestion -------------------------------------------------------------------


def test_create_assigns_sequential_reference_and_pending_suggestion(client, ctx):
    login(client, ctx["AGENT"])
    first = create(client, ctx)
    second = create(client, ctx)
    year = datetime.now(UTC).year
    assert first["reference"] == f"DEM-{year}-00001"
    assert second["reference"] == f"DEM-{year}-00002"
    assert first["status"] == "NEW" and first["priority"] is None
    s = first["suggestion"]
    assert s["decision"] == "PENDING" and s["provider"] == "mock-rules-v1"
    assert s["proposal"]["category_code"] == "DELIVERY"
    assert 0 <= s["confidence"] <= 1 and s["explanation"]
    assert [e["event_type"] for e in first["events"]] == ["created", "ai_suggested"]


@pytest.mark.parametrize(
    ("role", "expected"), [("ADMIN", 201), ("MANAGER", 201), ("AGENT", 201), ("VIEWER", 403)]
)
def test_create_permissions(client, ctx, role, expected):
    login(client, ctx[role])
    body = {**DELIVERY_TEXT, "account_id": str(ctx["account"].id)}
    assert client.post("/api/requests", json=body).status_code == expected


def test_create_validates_input_and_account_organization(client, ctx, db):
    other = setup_module_data(db, make_org(db, "Autre org"))
    login(client, ctx["AGENT"])
    assert (
        client.post(
            "/api/requests", json={**DELIVERY_TEXT, "account_id": str(ctx["account"].id), "title": "x"}
        ).status_code
        == 422
    )
    r = client.post("/api/requests", json={**DELIVERY_TEXT, "account_id": str(other["account"].id)})
    assert r.status_code == 422


# --- Décision sur la suggestion ---------------------------------------------------------------


def test_accept_classifies_and_sets_sla_due_dates(client, ctx, db):
    login(client, ctx["AGENT"])
    detail = accept(client, create(client, ctx))
    assert detail["status"] == "CLASSIFIED"
    assert detail["suggestion"]["decision"] == "ACCEPTED"
    assert detail["category"]["name"] == "Livraison et suivi"
    created = datetime.fromisoformat(detail["created_at"])
    resp, reso = SLA[Priority(detail["priority"])]
    assert datetime.fromisoformat(detail["due_response_at"]) == created + timedelta(minutes=resp)
    assert datetime.fromisoformat(detail["due_resolution_at"]) == created + timedelta(minutes=reso)
    assert "ai_suggestion.decided" in db.scalars(select(AuditLog.action)).all()


def test_modify_records_final_values(client, ctx):
    login(client, ctx["AGENT"])
    detail = create(client, ctx)
    r = client.post(
        f"/api/suggestions/{detail['suggestion']['id']}/decision",
        json={"action": "modify", "priority": "CRITICAL"},
    )
    assert r.status_code == 200
    out = r.json()
    assert out["priority"] == "CRITICAL" and out["status"] == "CLASSIFIED"
    assert out["suggestion"]["decision"] == "MODIFIED"
    assert out["suggestion"]["final_value"]["priority"] == "CRITICAL"


def test_reject_changes_nothing_and_decision_is_final(client, ctx):
    login(client, ctx["AGENT"])
    detail = create(client, ctx)
    url = f"/api/suggestions/{detail['suggestion']['id']}/decision"
    out = client.post(url, json={"action": "reject", "reason": "Hors sujet"}).json()
    assert out["status"] == "NEW" and out["category"] is None
    assert out["suggestion"]["decision"] == "REJECTED"
    assert client.post(url, json={"action": "accept"}).status_code == 409
    # Une nouvelle suggestion peut être demandée une fois la précédente traitée.
    again = client.post(f"/api/requests/{detail['id']}/suggestion")
    assert again.status_code == 200 and again.json()["suggestion"]["decision"] == "PENDING"


def test_viewer_cannot_decide(client, ctx):
    login(client, ctx["AGENT"])
    detail = create(client, ctx)
    login(client, ctx["VIEWER"])
    r = client.post(f"/api/suggestions/{detail['suggestion']['id']}/decision", json={"action": "accept"})
    assert r.status_code == 403


# --- Cycle de vie -----------------------------------------------------------------------------


def test_assignment_requires_team_member_and_drives_status(client, ctx):
    login(client, ctx["MANAGER"])
    detail = accept(client, create(client, ctx))  # équipe SUPPORT
    r = client.patch(f"/api/requests/{detail['id']}", json={"assignee_id": str(ctx["sav_agent"].id)})
    assert r.status_code == 422
    detail = assign(client, detail, ctx["AGENT"])
    assert detail["status"] == "ASSIGNED"
    detail = client.patch(f"/api/requests/{detail['id']}", json={"assignee_id": None}).json()
    assert detail["status"] == "CLASSIFIED"


def test_full_lifecycle_with_controlled_transitions(client, ctx, db):
    login(client, ctx["AGENT"])
    detail = assign(client, accept(client, create(client, ctx)), ctx["AGENT"])
    assert detail["allowed_transitions"] == ["IN_PROGRESS"]
    assert move(client, detail, "RESOLVED", "trop tôt").status_code == 409

    detail = move(client, detail, "IN_PROGRESS").json()
    assert detail["first_response_at"] is not None
    assert move(client, detail, "WAITING_INFO").status_code == 422  # commentaire obligatoire
    detail = move(client, detail, "WAITING_INFO", "Numéro de commande ?").json()
    detail = move(client, detail, "IN_PROGRESS").json()
    detail = move(client, detail, "RESOLVED", "Colis relivré ce matin.").json()
    assert detail["resolved_at"] is not None and detail["sla_state"] == "MET"
    assert [c["body"] for c in detail["comments"]] == ["Numéro de commande ?", "Colis relivré ce matin."]

    reopened = move(client, detail, "IN_PROGRESS").json()
    assert reopened["resolved_at"] is None
    detail = move(client, reopened, "RESOLVED", "Confirmé par le client.").json()
    detail = move(client, detail, "CLOSED").json()
    assert detail["closed_at"] is not None and detail["can_edit"] is False
    assert client.patch(f"/api/requests/{detail['id']}", json={"title": "Nouveau titre"}).status_code == 403


def test_in_progress_request_must_stay_assigned(client, ctx):
    login(client, ctx["AGENT"])
    detail = move(
        client, assign(client, accept(client, create(client, ctx)), ctx["AGENT"]), "IN_PROGRESS"
    ).json()
    assert client.patch(f"/api/requests/{detail['id']}", json={"assignee_id": None}).status_code == 422
    # Changer d'équipe sans réaffecter vide l'affectation : refusé pour une demande en cours.
    r = client.patch(f"/api/requests/{detail['id']}", json={"team_id": str(ctx["teams"]["AFTER_SALES"].id)})
    assert r.status_code == 422
    r = client.patch(
        f"/api/requests/{detail['id']}",
        json={"team_id": str(ctx["teams"]["AFTER_SALES"].id), "assignee_id": str(ctx["sav_agent"].id)},
    )
    assert r.status_code == 200 and r.json()["assignee"]["full_name"] == "Agent SAV"


def test_history_keeps_before_and_after(client, ctx, db):
    login(client, ctx["AGENT"])
    detail = accept(client, create(client, ctx))
    client.patch(f"/api/requests/{detail['id']}", json={"priority": "HIGH"})
    events = db.scalars(select(RequestEvent).where(RequestEvent.field == "priority")).all()
    assert [(e.old_value, e.new_value) for e in events][-1] == ("MEDIUM", "HIGH")
    req = db.get(ServiceRequest, detail["id"])
    assert req.due_resolution_at == req.created_at + timedelta(minutes=SLA[Priority.HIGH][1])


# --- Droits et visibilité ---------------------------------------------------------------------


def test_agent_sees_own_teams_and_unrouted_only(client, ctx):
    login(client, ctx["MANAGER"])
    sav = create(
        client, ctx, title="Produit défectueux", description="Appareil défectueux, retour sous garantie."
    )
    accept(client, sav)  # routée vers AFTER_SALES
    unrouted = create(client, ctx)

    login(client, ctx["AGENT"])  # équipe SUPPORT
    ids = {r["id"] for r in client.get("/api/requests").json()["items"]}
    assert unrouted["id"] in ids and sav["id"] not in ids
    assert client.get(f"/api/requests/{sav['id']}").status_code == 404

    login(client, ctx["sav_agent"])
    assert client.get(f"/api/requests/{sav['id']}").status_code == 200


def test_organizations_are_isolated(client, ctx, db):
    other = setup_module_data(db, make_org(db, "Autre org"))
    login(client, ctx["AGENT"])
    detail = create(client, ctx)
    login(client, other["ADMIN"])
    assert client.get(f"/api/requests/{detail['id']}").status_code == 404
    assert client.get("/api/requests").json()["total"] == 0
    r = client.post(f"/api/suggestions/{detail['suggestion']['id']}/decision", json={"action": "accept"})
    assert r.status_code == 404


# --- Liste, filtres, indicateurs --------------------------------------------------------------


def test_filters_search_and_overdue(client, ctx, db):
    login(client, ctx["MANAGER"])
    late = accept(client, create(client, ctx))
    create(client, ctx, title="Facture erronée", description="Le montant de la facture est faux, merci.")
    req = db.get(ServiceRequest, late["id"])
    req.created_at = req.created_at - timedelta(days=10)
    service.refresh_due_dates(db, req)
    db.commit()

    assert client.get("/api/requests", params={"overdue": True}).json()["total"] == 1
    assert client.get("/api/requests", params={"status": "NEW"}).json()["total"] == 1
    assert client.get("/api/requests", params={"q": "facture"}).json()["total"] == 1
    assert client.get("/api/requests", params={"q": "Client Standard"}).json()["total"] == 2
    by_category = client.get("/api/requests", params={"category_id": late["category"]["id"]}).json()
    assert [r["id"] for r in by_category["items"]] == [late["id"]]
    row = client.get("/api/requests", params={"overdue": True}).json()["items"][0]
    assert row["sla_state"] == "BREACHED"

    stats = client.get("/api/requests/stats").json()
    assert stats["open"] == 2 and stats["overdue"] == 1 and stats["to_classify"] == 1
    assert stats["ai_decisions"]["ACCEPTED"] == 1
    support = next(t for t in stats["by_team"] if t["team"]["code"] == "SUPPORT")
    assert support == {**support, "open": 1, "overdue": 1, "unassigned": 1}


def test_sla_state_rules():
    t0 = datetime(2026, 11, 1, 9, tzinfo=UTC)
    req = ServiceRequest(
        created_at=t0, due_response_at=t0 + timedelta(hours=4), due_resolution_at=t0 + timedelta(hours=24)
    )
    assert sla_state(req, t0 + timedelta(hours=1))[0] == "ON_TRACK"
    assert sla_state(req, t0 + timedelta(hours=3, minutes=30))[0] == "AT_RISK"
    assert sla_state(req, t0 + timedelta(hours=5))[0] == "BREACHED"  # prise en charge dépassée
    req.first_response_at = t0 + timedelta(hours=2)
    assert sla_state(req, t0 + timedelta(hours=5)) == ("ON_TRACK", t0 + timedelta(hours=24))
    assert sla_state(req, t0 + timedelta(hours=20))[0] == "AT_RISK"
    req.resolved_at = t0 + timedelta(hours=30)
    assert sla_state(req, t0 + timedelta(hours=31))[0] == "BREACHED"
    req.resolved_at = t0 + timedelta(hours=10)
    assert sla_state(req, t0 + timedelta(hours=31))[0] == "MET"
    assert sla_state(ServiceRequest(created_at=t0), t0)[0] == "NONE"


# --- Pièces jointes ---------------------------------------------------------------------------


def test_attachments_accept_pdf_only_and_are_hashed(client, ctx):
    login(client, ctx["AGENT"])
    detail = create(client, ctx)
    url = f"/api/requests/{detail['id']}/attachments"
    pdf = b"%PDF-1.4\n%fake but valid header\n"
    r = client.post(url, files={"file": ("bon.pdf", pdf, "application/pdf")})
    assert r.status_code == 201
    assert r.json()["size_bytes"] == len(pdf) and len(r.json()["sha256"]) == 64
    # Extension .pdf mais contenu texte : refusé (contrôle sur le contenu, NFR-03).
    assert client.post(url, files={"file": ("faux.pdf", b"hello", "application/pdf")}).status_code == 415
    got = client.get(f"{url}/{r.json()['id']}")
    assert got.status_code == 200 and got.content == pdf


def test_attachment_size_limit(client, ctx, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    login(client, ctx["AGENT"])
    detail = create(client, ctx)
    r = client.post(f"/api/requests/{detail['id']}/attachments", files={"file": ("a.pdf", b"%PDF-1", "x")})
    assert r.status_code == 413


# --- IA : repli et évaluation -----------------------------------------------------------------


class _Failing:
    name = "claude:test"

    def suggest(self, item, categories, teams):
        raise TriageError("délai dépassé")


class _Inventing:
    name = "claude:test"

    def suggest(self, item, categories, teams):
        return TriageProposal(
            category_code="INVENTE",
            priority="HIGH",
            team_code="SUPPORT",
            confidence={"category": 0.9, "priority": 0.9, "team": 0.9},
            explanation="?",
        )


@pytest.mark.parametrize("provider", [_Failing(), _Inventing()])
def test_provider_failure_falls_back_to_rules(db, ctx, provider):
    agent = db.get(User, ctx["AGENT"].id)
    req = service.create_request(
        db, agent, ctx["account"].id, Channel.EMAIL, DELIVERY_TEXT["title"], DELIVERY_TEXT["description"]
    )
    suggestion = service.suggest_triage(db, req, provider)
    assert suggestion is not None
    assert suggestion.provider == "mock-rules-v1 (repli)"
    assert suggestion.proposal["category_code"] == "DELIVERY"
    assert suggestion.explanation.startswith("[Repli sur les règles")


@pytest.mark.parametrize(("role", "expected"), [("MANAGER", 200), ("ADMIN", 200), ("AGENT", 403)])
def test_quality_report_permissions_and_content(client, ctx, role, expected):
    login(client, ctx[role])
    r = client.get("/api/ai/triage/quality")
    assert r.status_code == expected
    if expected == 200:
        offline = r.json()["offline"]
        assert offline["split"] == "test" and offline["size"] == 30
        assert {f["field"] for f in offline["fields"]} == {"category", "priority", "team"}


def test_premium_account_raises_priority(client, ctx):
    login(client, ctx["AGENT"])
    std = create(client, ctx)
    prem = create(client, ctx, account_id=str(ctx["premium"].id))
    assert std["suggestion"]["proposal"]["priority"] == "MEDIUM"
    assert prem["suggestion"]["proposal"]["priority"] == "HIGH"


def test_sla_update_is_admin_only_and_audited(client, ctx, db):
    login(client, ctx["MANAGER"])
    body = {"response_minutes": 30, "resolution_minutes": 240}
    assert client.put("/api/reference/sla/CRITICAL", json=body).status_code == 403
    login(client, ctx["ADMIN"])
    assert (
        client.put("/api/reference/sla/CRITICAL", json={**body, "resolution_minutes": 10}).status_code == 422
    )
    assert client.put("/api/reference/sla/CRITICAL", json=body).status_code == 200
    assert "sla.updated" in db.scalars(select(AuditLog.action)).all()
    ref = client.get("/api/reference").json()
    assert ref["sla"][-1] == {"priority": "CRITICAL", **body}
    assert ref["ai_provider"] == "mock-rules-v1"
