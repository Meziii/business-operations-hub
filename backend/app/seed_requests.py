"""Données de démonstration du module Demandes (synthétiques, reproductibles).

Les 60 demandes reprennent les textes du jeu étiqueté. Leur parcours est rejoué avec les vraies
règles de gestion (service.py), à des dates passées, pour obtenir un historique cohérent.
Les décisions sur les suggestions sont simulées à partir des étiquettes : l'agent fictif accepte
quand la proposition est juste et corrige sinon. Ces chiffres illustrent l'écran ; ils ne mesurent
pas un usage réel.
"""

import json
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.evaluate import DATASET
from app.ai.triage import MockTriageProvider
from app.demo_catalog import ACCOUNTS, CATEGORIES, SLA
from app.models import (
    Account,
    AccountTier,
    Category,
    Channel,
    Organization,
    Priority,
    Role,
    SlaPolicy,
    Status,
    Team,
    User,
)
from app.modules.requests import service

RESOLUTION_NOTES = [
    "Solution communiquée au client, qui confirme la résolution.",
    "Correction effectuée et confirmée par écrit au client.",
    "Échange réalisé, le client a reçu le nouveau produit.",
    "Information transmise au client par téléphone puis par e-mail.",
]
# Scénario de démonstration : quelques demandes du jour à classer, un historique majoritairement
# traité dans les délais, quelques dossiers en retard. Paramètres de mise en scène, pas des mesures.
TO_CLASSIFY = 8
FORGOTTEN_SHARE = 0.10  # dossiers anciens restés ouverts
LATE_SHARE = 0.10  # dossiers résolus après l'échéance

WAITING_NOTES = [
    "En attente du numéro de série et d'une photo du produit.",
    "En attente du bon de commande signé.",
    "Demande de précisions envoyée au client.",
]


def seed_requests(db: Session, org: Organization) -> int:
    """Charge le module Demandes si l'organisation n'a aucune catégorie. Renvoie le nombre de demandes."""
    if db.scalar(select(Category.id).where(Category.organization_id == org.id).limit(1)):
        return 0
    rng = random.Random(2026)
    teams = {t.code: t for t in db.scalars(select(Team).where(Team.organization_id == org.id))}
    for code, name, desc, team_code in CATEGORIES:
        db.add(
            Category(
                organization_id=org.id,
                code=code,
                name=name,
                description=desc,
                default_team_id=teams[team_code].id if team_code in teams else None,
            )
        )
    for prio, (resp, reso) in SLA.items():
        db.add(
            SlaPolicy(organization_id=org.id, priority=prio, response_minutes=resp, resolution_minutes=reso)
        )
    accounts = [
        Account(organization_id=org.id, name=n, type=t, tier=tier, is_synthetic=True)
        for n, t, tier in ACCOUNTS
    ]
    db.add_all(accounts)
    db.flush()

    users = list(db.scalars(select(User).where(User.organization_id == org.id)))
    agents = [u for u in users if u.role == Role.AGENT]
    manager = next((u for u in users if u.role == Role.MANAGER), agents[0])
    cats = {c.code: c for c in db.scalars(select(Category).where(Category.organization_id == org.id))}
    rows = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    rng.shuffle(rows)

    now = datetime.now(UTC).replace(second=0, microsecond=0)
    provider = MockTriageProvider()
    classified = len(rows) - TO_CLASSIFY
    for i, row in enumerate(rows):
        # Les demandes à classer sont arrivées dans la journée ; les autres s'étalent sur
        # environ trois semaines, plus serrées sur les derniers jours (travail en cours).
        if i >= classified:
            age_hours = rng.uniform(0.5, 10)
        else:
            rank = (classified - 1 - i) / (classified - 1)  # 0 = la plus récente, 1 = la plus ancienne
            age_hours = 10 + rank**2 * 480 + rng.uniform(0, 3)
        t = (now - timedelta(hours=age_hours)).replace(second=0, microsecond=0)
        tier = AccountTier(row["tier"])
        account = rng.choice([a for a in accounts if a.tier == tier])
        creator = rng.choice(agents)
        with service.frozen_clock(t):
            req = service.create_request(
                db,
                creator,
                account.id,
                Channel(row["channel"]),
                row["title"],
                row["description"],
                is_synthetic=True,
            )
            suggestion = service.suggest_triage(db, req, provider)
        if i >= classified or suggestion is None:
            continue

        # Classement par un agent, quelques minutes plus tard.
        t += timedelta(minutes=rng.randint(10, 90))
        category = cats[row["category"]]
        team = category.default_team
        right = (
            suggestion.proposal["category_code"] == row["category"]
            and suggestion.proposal["priority"] == row["priority"]
        )
        team_agents = [a for a in agents if team in a.teams] or agents
        decider = rng.choice(team_agents)
        with service.frozen_clock(t):
            if right:
                service.decide(db, suggestion, req, decider, "accept", None, None, None, None)
            else:
                service.decide(
                    db,
                    suggestion,
                    req,
                    decider,
                    "modify",
                    category.id,
                    Priority(row["priority"]),
                    team.id if team else None,
                    None,
                )

        # Affectation puis avancement selon l'âge de la demande, rapporté à son délai de résolution.
        # Étapes : 1 affectée, 2 en cours, 3 éventuellement en attente d'infos, 4 résolue, 5 clôturée.
        response_min, resolution_min = SLA[Priority(row["priority"])]
        sla_hours = resolution_min / 60
        if age_hours > sla_hours * 0.75:
            # Dossier ancien : en général traité ; quelques-uns oubliés, ce sont les retards visibles.
            steps = rng.choice([1, 2]) if rng.random() < FORGOTTEN_SHARE else rng.choice([4, 5, 5])
        else:
            steps = rng.choice([2, 2, 3])  # en cours de traitement
        assignee = rng.choice(team_agents)
        late = rng.random() < LATE_SHARE
        # Affectation et prise en charge rapides : dans le délai de prise en charge.
        quick = max(5, response_min // 4)
        for step in range(steps):
            t += (
                timedelta(minutes=rng.randint(5, quick))
                if step < 2
                else timedelta(hours=sla_hours * (rng.uniform(0.6, 0.9) if late else rng.uniform(0.1, 0.4)))
            )
            if t >= now:
                break
            with service.frozen_clock(t):
                if step == 0:
                    service.update_fields(db, req, manager, {"assignee_id": assignee.id})
                elif step == 1:
                    service.transition(db, req, assignee, Status.IN_PROGRESS, None)
                elif step == 2 and rng.random() < 0.3:
                    service.transition(db, req, assignee, Status.WAITING_INFO, rng.choice(WAITING_NOTES))
                    t += timedelta(hours=rng.randint(2, 20))
                    if t < now:
                        with service.frozen_clock(t):
                            service.transition(db, req, assignee, Status.IN_PROGRESS, None)
                elif step == 3 and req.status == Status.IN_PROGRESS:
                    service.transition(db, req, assignee, Status.RESOLVED, rng.choice(RESOLUTION_NOTES))
                elif step == 4 and req.status == Status.RESOLVED:
                    service.transition(db, req, manager, Status.CLOSED, None)
    db.flush()
    return len(rows)
