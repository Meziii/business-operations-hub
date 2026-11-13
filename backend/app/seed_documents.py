"""Données de démonstration du module Documents (synthétiques, reproductibles).

Un sous-ensemble du jeu étiqueté est fabriqué en PDF (eval/render.py), puis passé par la vraie
chaîne de traitement (ingest : texte/OCR, extraction, contrôles). Quelques documents sont ensuite
corrigés et validés, d'autres rejetés, pour que la démonstration montre tous les états. Ces décisions
illustrent les écrans ; elles ne mesurent pas un usage réel.
"""

import json
import random
from datetime import timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Anomaly, DocType, Document, Organization, Role, ServiceRequest, User
from app.modules.documents import service
from app.modules.documents.eval.render import render_text_pdf
from app.modules.documents.extract import MockDocumentExtractor
from app.modules.requests.service import frozen_clock, now

DATASET = Path(__file__).parent / "modules" / "documents" / "eval" / "documents_dataset.jsonl"
# Documents présentés : mélange de factures et garanties, avec des anomalies parlantes.
# D003 total incohérent (corrigé puis validé), D009 doublon de D002 (laissé à vérifier),
# D007 échéance douteuse (avertissement). Ordre choisi pour répartir validés / rejetés / à vérifier.
SHOWN = ["D003", "D001", "D002", "D027", "D007", "D025", "D009", "D028", "D031", "D004"]


def seed_documents(db: Session, org: Organization) -> int:
    """Charge le module Documents si l'organisation n'a aucun document. Renvoie le nombre créés."""
    if db.scalar(select(Document.id).where(Document.organization_id == org.id).limit(1)):
        return 0
    rng = random.Random(2026)
    rows = {
        r["id"]: r for r in (json.loads(x) for x in DATASET.read_text(encoding="utf-8").splitlines() if x)
    }
    users = list(db.scalars(select(User).where(User.organization_id == org.id)))
    agents = [u for u in users if u.role == Role.AGENT]
    manager = next((u for u in users if u.role == Role.MANAGER), agents[0])
    requests = list(
        db.scalars(
            select(ServiceRequest)
            .where(ServiceRequest.organization_id == org.id)
            .order_by(ServiceRequest.created_at)
        )
    )
    extractor = MockDocumentExtractor()

    created = 0
    for i, doc_id in enumerate(SHOWN):
        row = rows[doc_id]
        doc_type = DocType(row["doc_type"])
        agent = rng.choice(agents)
        when = (now() - timedelta(hours=int((len(SHOWN) - i) * 9) + rng.randint(0, 5))).replace(
            second=0, microsecond=0
        )
        # Rattacher les garanties à une demande déjà existante à cette date (événement jamais antérieur).
        request = None
        if doc_type == DocType.WARRANTY_CLAIM:
            earlier = [r for r in requests if r.created_at <= when]
            if earlier:
                request = rng.choice(earlier)
        with frozen_clock(when):
            doc = service.ingest(
                db,
                agent,
                render_text_pdf(row),
                f"{row['doc_type'].lower()}-{doc_id}.pdf",
                doc_type,
                request,
                extractor,
                is_synthetic=True,
            )
        created += 1

        # Décisions simulées : une partie validée (corrigée si besoin), une rejetée, le reste à vérifier.
        blocking = service.blocking(db, doc.id)
        decision = i % 5
        with frozen_clock((when + timedelta(minutes=rng.randint(15, 240))).replace(second=0, microsecond=0)):
            if decision in (0, 1, 2):
                current = service.latest_extraction(db, doc.id)
                assert current is not None
                fixes = {a.field: _repaired(row, a) for a in blocking if a.field}
                fixes = {k: v for k, v in fixes.items() if v is not None}
                if fixes:
                    service.correct(db, doc, agent, fixes)
                if not service.blocking(db, doc.id):
                    service.validate(db, doc, manager if decision == 2 else agent)
            elif decision == 3:
                service.reject(db, doc, agent, "Document sans objet pour notre organisation.")
            # decision == 4 : laissé « à vérifier »
    db.flush()
    return created


def _repaired(row: dict[str, Any], anomaly: Anomaly) -> object:
    """Valeur de correction plausible pour lever une anomalie bloquante d'après l'étiquette du jeu."""
    expected = row["expected"]
    if anomaly.code == "INCONSISTENT_TOTAL":
        return round(expected["total_excl_tax"] + expected["vat_amount"], 2)
    if anomaly.code == "MISSING_FIELD" and anomaly.field:
        return expected.get(anomaly.field)
    if anomaly.code == "FAILURE_BEFORE_PURCHASE":
        return expected["failure_date"]
    return None
