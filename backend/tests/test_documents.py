"""Module 2 — documents : dépôt, lecture, extraction, contrôles, correction, décision, rattachement."""

import json
from datetime import date

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.models import AiSuggestion, AuditLog, Decision, RequestEvent
from app.modules.documents import controls
from app.modules.documents.eval.render import render_scan, render_text_pdf
from app.modules.documents.evaluate import DATASET, evaluate
from app.modules.documents.extract import ExtractionError, MockDocumentExtractor, parse_amount, parse_date
from app.modules.documents.text import ocr_available
from tests.conftest import login, make_org
from tests.test_requests import create, setup_module_data

ROWS = {r["id"]: r for r in (json.loads(x) for x in DATASET.read_text(encoding="utf-8").splitlines() if x)}
CLEAN_INVOICE = "D001"  # facture A, valeurs cohérentes
WRONG_TOTAL = "D003"  # facture A, total TTC faux (INCONSISTENT_TOTAL)
WARRANTY = "D025"  # garantie, formulaire


@pytest.fixture
def ctx(db):
    return setup_module_data(db, make_org(db))


def pdf(doc_id: str) -> bytes:
    return render_text_pdf(ROWS[doc_id])


def upload(client, doc_id: str, doc_type: str = "INVOICE", request_id=None, content: bytes | None = None):
    data = {"doc_type": doc_type}
    if request_id:
        data["request_id"] = str(request_id)
    files = {"file": (f"{doc_id}.pdf", content if content is not None else pdf(doc_id), "application/pdf")}
    return client.post("/api/documents", data=data, files=files)


def values(detail) -> dict:
    return {f["name"]: f["value"] for f in detail["fields"]}


# --- Analyse des valeurs et contrôles (fonctions pures) -------------------------------------------


def test_parse_amount_and_date_formats():
    assert parse_amount("4 239,94") == 4239.94
    assert parse_amount("6337,71") == 6337.71
    assert parse_amount("4,295.44") == 4295.44
    assert parse_amount("EUR 10 201,27") == 10201.27
    assert parse_amount("1.234,56") == 1234.56
    assert parse_date("21/10/2026") == "2026-10-21"
    assert parse_date("9 octobre 2026") == "2026-10-09"
    assert parse_date("1er août 2025") == "2025-08-01"
    assert parse_date("2026-06-16") == "2026-06-16"
    assert parse_date("31/02/2026") is None


def test_controls_rules():
    today = date(2026, 11, 13)
    ok = {
        "invoice_number": "F-1",
        "invoice_date": "2026-10-01",
        "due_date": "2026-11-01",
        "supplier_name": "A",
        "customer_name": "B",
        "order_reference": None,
        "total_excl_tax": 100.0,
        "vat_amount": 20.0,
        "total_incl_tax": 120.0,
    }
    assert controls.check("INVOICE", ok, today) == []
    codes = lambda data, dups=None: {f.code for f in controls.check("INVOICE", {**ok, **data}, today, dups)}  # noqa: E731
    assert codes({"total_incl_tax": 130.0}) == {"INCONSISTENT_TOTAL"}
    assert codes({"total_incl_tax": 120.01}) == set()  # arrondi toléré
    assert codes({"vat_amount": 13.0, "total_incl_tax": 113.0}) == {"UNUSUAL_VAT_RATE"}
    assert codes({"due_date": "2026-09-01"}) == {"DUE_BEFORE_INVOICE"}
    assert codes({"invoice_number": None}) == {"MISSING_FIELD"}
    assert codes({"invoice_date": "2026-12-01", "due_date": "2027-01-01"}) == {"DATE_IN_FUTURE"}
    assert codes({}, ["DOC-2026-00001"]) == {"DUPLICATE"}

    claim = {
        "customer_name": "B",
        "product_reference": "PRD-1",
        "serial_number": "SN-1",
        "purchase_date": "2025-01-10",
        "failure_date": "2026-01-10",
        "invoice_number": None,
        "failure_description": "Panne",
    }
    wcodes = lambda data: {f.code for f in controls.check("WARRANTY_CLAIM", {**claim, **data}, today)}  # noqa: E731
    assert wcodes({}) == set()
    assert wcodes({"failure_date": "2024-12-01"}) == {"FAILURE_BEFORE_PURCHASE"}
    assert wcodes({"purchase_date": "2023-06-01"}) == {"OUT_OF_WARRANTY"}
    blocking = {
        f.code
        for f in controls.check("INVOICE", {**ok, "total_incl_tax": 1.0}, today)
        if f.severity == "BLOCKING"
    }
    assert blocking == {"INCONSISTENT_TOTAL"}


def test_rules_read_every_dev_text_document():
    """Les règles ont été écrites sur le split dev : elles doivent y lire tous les PDF texte."""
    report = evaluate(MockDocumentExtractor(), "dev")
    assert report.text_accuracy == 1.0
    assert all(f.accuracy == 1.0 for f in report.fields)


# --- Dépôt et lecture -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("role", "expected"), [("ADMIN", 201), ("MANAGER", 201), ("AGENT", 201), ("VIEWER", 403)]
)
def test_upload_permissions(client, ctx, role, expected):
    login(client, ctx[role])
    assert upload(client, CLEAN_INVOICE).status_code == expected


def test_upload_extracts_invoice_fields(client, ctx, db):
    login(client, ctx["AGENT"])
    r = upload(client, CLEAN_INVOICE)
    assert r.status_code == 201, r.text
    detail = r.json()
    assert detail["reference"].startswith("DOC-") and detail["reference"].endswith("-00001")
    assert detail["status"] == "TO_REVIEW" and detail["ocr_pages"] == 0 and detail["page_count"] == 1
    expected = ROWS[CLEAN_INVOICE]["expected"]
    got = values(detail)
    for name, value in expected.items():
        assert got[name] == value, name
    assert detail["anomalies"] == [] and detail["can_edit"] is True
    assert all(f["confidence"] >= 0.6 for f in detail["fields"] if f["value"] is not None)
    suggestion = db.scalar(select(AiSuggestion).where(AiSuggestion.kind == "extraction"))
    assert suggestion.decision == Decision.PENDING and suggestion.provider == "mock-rules-v1"


def test_upload_rejects_non_pdf_and_large_files(client, ctx, monkeypatch):
    login(client, ctx["AGENT"])
    assert upload(client, CLEAN_INVOICE, content=b"ceci n'est pas un pdf").status_code == 415
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    assert upload(client, CLEAN_INVOICE).status_code == 413


def test_corrupted_pdf_is_kept_for_manual_entry(client, ctx):
    login(client, ctx["AGENT"])
    r = upload(client, CLEAN_INVOICE, content=b"%PDF-1.4 tronque")
    assert r.status_code == 201
    detail = r.json()
    assert detail["text_error"] and all(f["value"] is None for f in detail["fields"])
    assert {a["code"] for a in detail["anomalies"]} == {"MISSING_FIELD"}


@pytest.mark.skipif(not ocr_available(), reason="Tesseract absent : OCR testé en CI et dans Docker")
def test_scanned_document_goes_through_ocr(client, ctx):
    login(client, ctx["AGENT"])
    scan = render_scan(pdf(CLEAN_INVOICE), CLEAN_INVOICE)
    detail = upload(client, CLEAN_INVOICE, content=scan).json()
    assert detail["ocr_pages"] == 1 and detail["ocr_used"] is True and detail["ocr_confidence"] > 0.5
    assert values(detail)["invoice_number"] == ROWS[CLEAN_INVOICE]["expected"]["invoice_number"]


def test_failing_provider_falls_back_to_rules(db, ctx):
    from app.models import DocType, User
    from app.modules.documents import service

    class Failing:
        name = "claude:test"

        def extract(self, *args):
            raise ExtractionError("délai dépassé")

    agent = db.get(User, ctx["AGENT"].id)
    doc = service.ingest(db, agent, pdf(CLEAN_INVOICE), "f.pdf", DocType.INVOICE, extractor=Failing())
    v1 = service.latest_extraction(db, doc.id)
    assert v1.provider == "mock-rules-v1 (repli)"
    assert v1.data["invoice_number"] == ROWS[CLEAN_INVOICE]["expected"]["invoice_number"]


# --- Contrôles, correction, décision -------------------------------------------------------------------


def test_blocking_anomaly_prevents_validation_until_corrected(client, ctx, db):
    login(client, ctx["AGENT"])
    detail = upload(client, WRONG_TOTAL).json()
    assert [a["code"] for a in detail["anomalies"]] == ["INCONSISTENT_TOTAL"]
    assert client.post(f"/api/documents/{detail['id']}/validate").status_code == 409

    fixed = round(values(detail)["total_excl_tax"] + values(detail)["vat_amount"], 2)
    r = client.patch(f"/api/documents/{detail['id']}/fields", json={"data": {"total_incl_tax": fixed}})
    assert r.status_code == 200, r.text
    detail = r.json()
    assert detail["anomalies"] == []
    field = next(f for f in detail["fields"] if f["name"] == "total_incl_tax")
    assert field["corrected"] is True and field["confidence"] == 1.0 and field["proposed"] != fixed
    assert [(v["version"], v["source"], v["changed"]) for v in detail["versions"]] == [
        (1, "AI", []),
        (2, "HUMAN", ["total_incl_tax"]),
    ]

    detail = client.post(f"/api/documents/{detail['id']}/validate").json()
    assert (
        detail["status"] == "VALIDATED" and detail["decision"] == "MODIFIED" and detail["can_edit"] is False
    )
    assert db.scalar(select(AuditLog).where(AuditLog.action == "document.validated")) is not None
    # Un document validé ne se modifie plus
    r = client.patch(f"/api/documents/{detail['id']}/fields", json={"data": {"invoice_number": "X"}})
    assert r.status_code == 409


def test_unchanged_extraction_is_accepted(client, ctx):
    login(client, ctx["AGENT"])
    detail = upload(client, CLEAN_INVOICE).json()
    detail = client.post(f"/api/documents/{detail['id']}/validate").json()
    assert detail["decision"] == "ACCEPTED"


def test_corrections_are_validated_by_schema(client, ctx):
    login(client, ctx["AGENT"])
    doc_id = upload(client, CLEAN_INVOICE).json()["id"]
    assert (
        client.patch(
            f"/api/documents/{doc_id}/fields", json={"data": {"invoice_date": "32/13/2026"}}
        ).status_code
        == 422
    )
    assert client.patch(f"/api/documents/{doc_id}/fields", json={"data": {"unknown": "x"}}).status_code == 422
    r = client.patch(f"/api/documents/{doc_id}/fields", json={"data": {"vat_amount": "abc"}})
    assert r.status_code == 422


def test_duplicates_are_blocking(client, ctx):
    login(client, ctx["AGENT"])
    first = upload(client, CLEAN_INVOICE).json()
    second = upload(client, CLEAN_INVOICE).json()  # même fichier, même émetteur et numéro
    dup = next(a for a in second["anomalies"] if a["code"] == "DUPLICATE")
    assert dup["severity"] == "BLOCKING" and first["reference"] in dup["message"]
    # Rejeter l'original lève le doublon à la prochaine version
    client.post(f"/api/documents/{first['id']}/reject", json={"reason": "Saisi deux fois"})
    detail = client.patch(
        f"/api/documents/{second['id']}/fields", json={"data": {"order_reference": "BC-1"}}
    ).json()
    assert "DUPLICATE" not in {a["code"] for a in detail["anomalies"]}


def test_reject_needs_a_reason_and_is_final(client, ctx, db):
    login(client, ctx["AGENT"])
    doc_id = upload(client, CLEAN_INVOICE).json()["id"]
    assert client.post(f"/api/documents/{doc_id}/reject", json={"reason": ""}).status_code == 422
    detail = client.post(f"/api/documents/{doc_id}/reject", json={"reason": "Pas pour nous"}).json()
    assert detail["status"] == "REJECTED" and detail["decision"] == "REJECTED"
    assert detail["rejection_reason"] == "Pas pour nous"
    assert client.post(f"/api/documents/{doc_id}/validate").status_code == 409
    assert client.put(f"/api/documents/{doc_id}/request", json={"request_id": None}).status_code == 409


def test_viewer_reads_but_cannot_act(client, ctx):
    login(client, ctx["AGENT"])
    doc_id = upload(client, WARRANTY, "WARRANTY_CLAIM").json()["id"]
    login(client, ctx["VIEWER"])
    detail = client.get(f"/api/documents/{doc_id}").json()
    assert (
        detail["can_edit"] is False
        and values(detail)["serial_number"] == ROWS[WARRANTY]["expected"]["serial_number"]
    )
    assert client.post(f"/api/documents/{doc_id}/validate").status_code == 403
    assert client.get(f"/api/documents/{doc_id}/file").status_code == 200


def test_organizations_are_isolated(client, ctx, db):
    other = make_org(db, "Autre org")
    login(client, ctx["AGENT"])
    doc_id = upload(client, CLEAN_INVOICE).json()["id"]
    login(client, other["ADMIN"])
    assert client.get(f"/api/documents/{doc_id}").status_code == 404
    assert client.get(f"/api/documents/{doc_id}/file").status_code == 404
    assert client.get("/api/documents").json()["total"] == 0


# --- Rattachement, liste, qualité ----------------------------------------------------------------------


def test_link_to_request_is_traced_on_both_sides(client, ctx, db):
    login(client, ctx["AGENT"])
    req = create(client, ctx)
    doc = upload(client, WARRANTY, "WARRANTY_CLAIM", request_id=req["id"]).json()
    assert doc["request"]["reference"] == req["reference"]
    detail = client.get(f"/api/requests/{req['id']}").json()
    assert [d["reference"] for d in detail["documents"]] == [doc["reference"]]
    events = db.scalars(select(RequestEvent).where(RequestEvent.event_type.like("document_%"))).all()
    assert [(e.event_type, e.new_value) for e in events] == [("document_linked", doc["reference"])]

    doc = client.put(f"/api/documents/{doc['id']}/request", json={"request_id": None}).json()
    assert doc["request"] is None
    assert client.get(f"/api/requests/{req['id']}").json()["documents"] == []


def test_cannot_link_to_an_invisible_request(client, ctx):
    login(client, ctx["MANAGER"])
    # Demande routée vers une équipe dont l'agent n'est pas membre
    req = create(client, ctx)
    client.patch(f"/api/requests/{req['id']}", json={"team_id": str(ctx["teams"]["SALES"].id)})
    login(client, ctx["AGENT"])
    r = upload(client, CLEAN_INVOICE, request_id=req["id"])
    assert r.status_code == 404


def test_list_filters_and_stats(client, ctx):
    login(client, ctx["AGENT"])
    upload(client, CLEAN_INVOICE)
    upload(client, WRONG_TOTAL)
    upload(client, WARRANTY, "WARRANTY_CLAIM")
    page = client.get("/api/documents").json()
    assert page["total"] == 3
    assert client.get("/api/documents", params={"doc_type": "WARRANTY_CLAIM"}).json()["total"] == 1
    assert client.get("/api/documents", params={"blocking_only": True}).json()["total"] == 1
    number = ROWS[CLEAN_INVOICE]["expected"]["invoice_number"]
    assert client.get("/api/documents", params={"q": number}).json()["total"] == 1
    stats = client.get("/api/documents/stats").json()
    assert stats == {"to_review": 3, "with_blocking": 1, "validated": 0, "rejected": 0}


@pytest.mark.parametrize(("role", "expected"), [("MANAGER", 200), ("ADMIN", 200), ("AGENT", 403)])
def test_quality_report_permissions(client, ctx, role, expected):
    login(client, ctx[role])
    r = client.get("/api/ai/extraction/quality")
    assert r.status_code == expected
    if expected == 200:
        body = r.json()
        assert body["offline"]["split"] == "test" and body["offline"]["size"] == 20
        assert body["dev_documents_fully_correct"] >= body["offline"]["documents_fully_correct"]
