"""Suggestion de catégorie, priorité et équipe pour une demande (US-201).

L'IA propose, un collaborateur décide (BR-05). Chaque fournisseur renvoie le même contrat
`TriageProposal` ; le service vérifie ensuite que les codes proposés existent bien.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, Field

PriorityCode = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
PRIORITY_ORDER: list[PriorityCode] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


@dataclass(frozen=True)
class CategoryOption:
    code: str
    name: str
    description: str
    default_team_code: str | None


@dataclass(frozen=True)
class TeamOption:
    code: str
    name: str


@dataclass(frozen=True)
class TriageInput:
    title: str
    description: str
    channel: str
    account_tier: str


class TriageProposal(BaseModel):
    category_code: str
    priority: PriorityCode
    team_code: str
    confidence: dict[str, float] = Field(description="Confiance par champ, entre 0 et 1")
    explanation: str

    @property
    def overall_confidence(self) -> float:
        return round(min(self.confidence.values()), 2) if self.confidence else 0.0


class TriageError(Exception):
    """Le fournisseur n'a pas pu produire une proposition exploitable."""


class TriageProvider(Protocol):
    name: str

    def suggest(
        self, item: TriageInput, categories: list[CategoryOption], teams: list[TeamOption]
    ) -> TriageProposal: ...


def normalize(text: str) -> str:
    """Minuscules, sans accents : « Facturé » et « facture » se comparent de la même façon."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


# Mots-clés par code de catégorie. Volontairement lisibles : c'est la référence à battre
# pour un modèle de langage, et l'explication montrée à l'agent cite les mots repérés.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "DELIVERY": [
        "livraison",
        "livre",
        "livrer",
        "colis",
        "transporteur",
        "expedition",
        "expedie",
        "retard de livraison",
        "suivi de commande",
        "numero de suivi",
        "pas recu",
        "jamais recu",
        "receptionne",
        "palette",
        "adresse de livraison",
    ],
    "ORDER": [
        "devis",
        "commande",
        "commander",
        "tarif",
        "prix",
        "remise",
        "disponibilite",
        "stock",
        "reference",
        "catalogue",
        "quantite",
        "bon de commande",
        "proforma",
    ],
    "BILLING": [
        "facture",
        "facturation",
        "avoir",
        "paiement",
        "payer",
        "prelevement",
        "virement",
        "relance de paiement",
        "echeance",
        "montant",
        "tva",
        "rib",
        "remboursement",
        "double facturation",
    ],
    "WARRANTY": [
        "garantie",
        "retour",
        "defectueux",
        "defaut",
        "casse",
        "endommage",
        "echange",
        "rma",
        "sous garantie",
        "remplacement",
        "non conforme",
        "panne",
    ],
    "TECHNICAL": [
        "installation",
        "configuration",
        "notice",
        "mode d'emploi",
        "fonctionne pas",
        "erreur",
        "code erreur",
        "parametrage",
        "compatibilite",
        "mise a jour",
        "firmware",
        "branchement",
        "technique",
        "diagnostic",
    ],
    "ACCOUNT": [
        "compte",
        "acces",
        "mot de passe",
        "identifiant",
        "connexion",
        "portail",
        "espace client",
        "utilisateur",
        "coordonnees",
        "changement d'adresse",
        "contact",
    ],
}

# Ordre de départage en cas d'égalité : du plus spécifique au plus général.
_TIE_BREAK = ["WARRANTY", "BILLING", "DELIVERY", "TECHNICAL", "ACCOUNT", "ORDER"]

PRIORITY_KEYWORDS: dict[PriorityCode, list[str]] = {
    "CRITICAL": [
        "production arretee",
        "arret de production",
        "ligne arretee",
        "bloquant",
        "bloque totalement",
        "securite",
        "danger",
        "plus rien ne fonctionne",
        "a l'arret",
    ],
    "HIGH": [
        "urgent",
        "urgence",
        "au plus vite",
        "rapidement",
        "des que possible",
        "aujourd'hui",
        "relance",
        "deuxieme relance",
        "inacceptable",
        "penalites",
        "bloque",
    ],
    "LOW": [
        "pour information",
        "simple question",
        "renseignement",
        "quand vous aurez le temps",
        "pas urgent",
        "a titre indicatif",
        "documentation",
        "curiosite",
    ],
}


_ACCENTS = {"a": "aàâä", "c": "cç", "e": "eéèêë", "i": "iîï", "o": "oôö", "u": "uùûü", "y": "yÿ"}
_PRIORITY_NAMES: dict[PriorityCode, str] = {
    "LOW": "Basse",
    "MEDIUM": "Normale",
    "HIGH": "Haute",
    "CRITICAL": "Critique",
}


def _as_written(original: str, keyword: str) -> str:
    """Retrouve un mot-clé normalisé tel qu'il est écrit dans le texte, pour l'explication."""
    pattern = "".join(
        f"[{_ACCENTS[ch]}]" if ch in _ACCENTS else r"[\s'’]" if ch in " '" else re.escape(ch)
        for ch in keyword
    )
    match = re.search(pattern, original, re.IGNORECASE)
    return match.group(0).lower() if match else keyword


def _hits(text: str, keywords: list[str]) -> list[str]:
    found = []
    for kw in dict.fromkeys(keywords):
        if re.search(rf"\b{re.escape(kw)}", text):
            found.append(kw)
    return found


class MockTriageProvider:
    """Règles par mots-clés, déterministes, sans appel externe (mode démonstration, NFR-04)."""

    name = "mock-rules-v1"

    def suggest(
        self, item: TriageInput, categories: list[CategoryOption], teams: list[TeamOption]
    ) -> TriageProposal:
        original = f"{item.title} {item.description}"
        text = normalize(original)
        available = {c.code: c for c in categories}
        if not available:
            raise TriageError("Aucune catégorie paramétrée.")

        scores = {code: _hits(text, kws) for code, kws in CATEGORY_KEYWORDS.items() if code in available}
        ranked = sorted(
            scores.items(),
            key=lambda kv: (len(kv[1]), -_TIE_BREAK.index(kv[0]) if kv[0] in _TIE_BREAK else 0),
            reverse=True,
        )
        reasons: list[str] = []
        if ranked and ranked[0][1]:
            code, words = ranked[0]
            runner_up = len(ranked[1][1]) if len(ranked) > 1 else 0
            margin = len(words) - runner_up
            cat_conf = 0.9 if margin >= 2 else 0.75 if margin == 1 else 0.55
            shown = ", ".join(f"« {_as_written(original, w)} »" for w in words[:4])
            reasons.append(f"catégorie « {available[code].name} » : mots repérés {shown}")
        else:
            code = "OTHER" if "OTHER" in available else next(iter(available))
            cat_conf = 0.3
            reasons.append("aucun mot-clé de catégorie repéré")

        priority: PriorityCode = "MEDIUM"
        prio_conf = 0.5
        # « pas urgent » ne doit pas déclencher la règle « urgent ».
        prio_text = re.sub(r"\b(pas|non|rien d)\W*(tres\W+)?urgent\w*", " pas urgent ", text)
        levels: tuple[PriorityCode, ...] = ("CRITICAL", "HIGH", "LOW")
        for level in levels:
            words = _hits(
                prio_text.replace("pas urgent", "pas_urgent") if level == "HIGH" else prio_text,
                PRIORITY_KEYWORDS[level],
            )
            if words:
                priority = level
                prio_conf = 0.75
                reasons.append(f"priorité {_PRIORITY_NAMES[level]} : « {_as_written(original, words[0])} »")
                break
        else:
            reasons.append("priorité Normale par défaut")
        if item.account_tier == "PREMIUM" and priority in ("LOW", "MEDIUM"):
            priority = PRIORITY_ORDER[PRIORITY_ORDER.index(priority) + 1]
            reasons.append(f"client Premium : priorité relevée d'un cran ({_PRIORITY_NAMES[priority]})")

        team_codes = {t.code for t in teams}
        team = available[code].default_team_code
        if team not in team_codes:
            team = next(iter(sorted(team_codes)), "")
            team_conf = 0.3
        else:
            team_conf = cat_conf
        reasons.append("équipe : équipe par défaut de la catégorie")

        return TriageProposal(
            category_code=code,
            priority=priority,
            team_code=team or "",
            confidence={"category": cat_conf, "priority": prio_conf, "team": team_conf},
            explanation="Règles de démonstration — " + " ; ".join(reasons) + ".",
        )
