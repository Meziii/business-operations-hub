"""Profils de démonstration : le fonctionnement reste le même, seul l'habillage sectoriel change.

Choisi par la variable DEMO_PROFILE. Toutes les organisations et personnes sont fictives.
"""

from dataclasses import dataclass, field

from app.models import Role


@dataclass(frozen=True)
class DemoProfile:
    organization: str
    sector: str
    teams: list[tuple[str, str]]
    users: list[tuple[str, str, Role, list[str]]] = field(default_factory=list)


# Équipes et utilisateurs communs : l'organisation du travail est la même quel que soit le secteur.
_TEAMS = [
    ("SUPPORT", "Support client"),
    ("AFTER_SALES", "Service après-vente"),
    ("SALES", "Équipe commerciale"),
    ("ADMIN_FIN", "Administration et comptabilité"),
]

_USERS = [
    ("admin@example.com", "Thomas Admin", Role.ADMIN, []),
    ("lucie.manager@example.com", "Lucie Responsable", Role.MANAGER, ["SUPPORT", "AFTER_SALES"]),
    ("sarah.support@example.com", "Sarah Support", Role.AGENT, ["SUPPORT"]),
    ("karim.sav@example.com", "Karim Après-vente", Role.AGENT, ["AFTER_SALES"]),
    ("nadia.sales@example.com", "Nadia Commerciale", Role.AGENT, ["SALES"]),
    ("paul.compta@example.com", "Paul Comptabilité", Role.AGENT, ["ADMIN_FIN"]),
    ("direction@example.com", "Claire Direction", Role.VIEWER, []),
]

PROFILES: dict[str, DemoProfile] = {
    "generic": DemoProfile("Démo — Distribution B2B", "Produits B2B multi-catégories", _TEAMS, _USERS),
    "automotive": DemoProfile("Démo — Équipementier automobile", "Produits automobiles", _TEAMS, _USERS),
    "industrial": DemoProfile("Démo — Fournitures industrielles", "Équipements industriels", _TEAMS, _USERS),
}
