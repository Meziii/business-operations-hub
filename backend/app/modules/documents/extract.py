"""Extraction des champs (BR-07) : interface commune, mode démonstration à base de règles.

Les règles ont été écrites à partir du split `dev` du jeu documentaire uniquement (factures A et B,
garanties F et L). Elles cherchent des libellés français ; une mise en page inconnue les met en
difficulté, c'est attendu et mesuré (voir docs/07-ai-governance/document-extraction-evaluation.md).
"""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

from pydantic import ValidationError

from app.modules.documents.fields import FIELDS, DocType, validate_fields


class ExtractionError(Exception):
    """Le fournisseur n'a pas produit d'extraction exploitable."""


@dataclass
class ExtractionResult:
    data: dict[str, Any]
    confidence: dict[str, float]
    provider: str
    notes: list[str] = field(default_factory=list)


class DocumentExtractor(Protocol):
    name: str

    def extract(self, doc_type: DocType, text: str, ocr_confidence: float | None) -> ExtractionResult: ...


# --- Analyse des valeurs ------------------------------------------------------------------------

MONTHS = {
    "janvier": 1,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
}
_AMOUNT = r"\d[\d\s.,]*\d|\d"
_DATE = r"\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}(?:er)?\s+[a-zA-Zéûô]+\s+\d{4}"


def _plain(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def parse_amount(raw: str) -> float | None:
    """« 4 239,94 », « 6337,71 », « 4,295.44 », « EUR 10 201,27 » → nombre. None si illisible."""
    s = re.sub(r"[^\d.,]", "", raw.replace(" ", " ").replace(" ", ""))
    if not s or not s[0].isdigit():
        return None
    last_comma, last_dot = s.rfind(","), s.rfind(".")
    sep = max(last_comma, last_dot)
    if sep != -1 and len(s) - sep - 1 == 2:
        whole, dec = s[:sep], s[sep + 1 :]
        whole = re.sub(r"[.,]", "", whole)
        s = f"{whole}.{dec}"
    else:
        s = re.sub(r"[.,]", "", s)
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def parse_date(raw: str) -> str | None:
    raw = raw.strip()
    try:
        if m := re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw):
            return date(int(m[3]), int(m[2]), int(m[1])).isoformat()
        if m := re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", raw):
            return date(int(m[1]), int(m[2]), int(m[3])).isoformat()
        if m := re.fullmatch(r"(\d{1,2})(?:er)?\s+(\S+)\s+(\d{4})", raw):
            month = MONTHS.get(_plain(m[2]))
            return date(int(m[3]), month, int(m[1])).isoformat() if month else None
    except ValueError:
        return None
    return None


# --- Mode démonstration ---------------------------------------------------------------------------

LABEL = 0.9  # valeur trouvée derrière un libellé explicite
HEURISTIC = 0.6  # valeur déduite de la position (première ligne, ligne suivante…)
# Bruit d'OCR en tête de valeur : barres, tirets de cadre, guillemets, deux-points, ponctuation isolée.
_LEAD = r"[\s|_¦“”\"':.,·•*]+"
# En fin de valeur on ne retire que les parasites, jamais le point ou la virgule d'une vraie phrase.
_TRAIL = r"[\s|_¦“”\"'·•*]+"
_SEP = r"[ \t:._|¦]*"  # entre un libellé et sa valeur, un scan glisse souvent des « | » ou « _ »


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = re.sub(rf"^{_LEAD}", "", re.sub(rf"{_TRAIL}$", "", value.strip()))
    return value or None


class _Finder:
    def __init__(self, text: str) -> None:
        self.text = text
        self.lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    def after_label(self, labels: str, value: str) -> str | None:
        """Valeur qui suit un libellé sur la même ligne (insensible à la casse, tolérante au bruit)."""
        labels = labels.replace(r"\s", r"[ \t]")  # ne jamais déborder sur la ligne suivante
        m = re.search(rf"(?:{labels})[ \t]*{_SEP}({value})", self.text, re.IGNORECASE | re.MULTILINE)
        return _clean(m.group(1)) if m else None

    def line_after(self, label: str) -> str | None:
        """Ligne qui suit un libellé seul sur sa ligne (le libellé peut traîner du bruit d'OCR)."""
        for i, ln in enumerate(self.lines[:-1]):
            if re.fullmatch(rf"{label}\s*:?(?:{_TRAIL})?", ln, re.IGNORECASE):
                return _clean(self.lines[i + 1])
        return None

    def first_line(self) -> str | None:
        return _clean(self.lines[0]) if self.lines else None


class MockDocumentExtractor:
    """Règles par libellés, déterministes, sans appel externe (mode démonstration, NFR-04)."""

    name = "mock-rules-v1"

    def extract(self, doc_type: DocType, text: str, ocr_confidence: float | None) -> ExtractionResult:
        f = _Finder(text)
        raw: dict[str, Any] = {}
        conf: dict[str, float] = {}

        def put(name: str, value: Any, c: float) -> None:
            if value is not None and value != "":
                raw[name], conf[name] = value, c

        if doc_type == "INVOICE":
            put(
                "invoice_number",
                f.after_label(r"N[°o*º]?\s*de\s*facture|Facture\s*n[°o*º]", r"[A-Z0-9][\w\-/]*\d[\w\-/]*"),
                LABEL,
            )
            d = f.after_label(r"(?<![a-z])Date|Facture\s*n[°o*º]?\s*[\w\-/]+\s+du", _DATE)
            put("invoice_date", parse_date(d) if d else None, LABEL)
            d = f.after_label(r"[ÉE]ch[ée]ance|[àa]\s*r[ée]gler\s*avant\s*le", _DATE)
            put("due_date", parse_date(d) if d else None, LABEL)
            put("supplier_name", f.first_line(), HEURISTIC)
            client = f.after_label(r"^Client", r"[^\n]+")
            if client:
                put("customer_name", client, LABEL)
            else:
                put("customer_name", f.line_after("Destinataire"), HEURISTIC)
            put("order_reference", f.after_label(r"commande[^:\n]*", r"[A-Z]{1,4}-?\d[\w\-]*"), LABEL)
            for name, labels in (
                ("total_excl_tax", r"Total\s*HT|Montant\s*HT"),
                ("vat_amount", r"TVA[^:\n\d]*(?:\(?\d+(?:[,.]\d+)?\s*%\)?)?"),
                ("total_incl_tax", r"Total\s*TTC|Net\s*[àa]\s*payer"),
            ):
                v = f.after_label(labels, _AMOUNT)
                put(name, parse_amount(v) if v else None, LABEL)
        else:
            client = f.after_label(r"^Client", r"[^\n]+")
            put("customer_name", client, LABEL) if client else put("customer_name", f.first_line(), HEURISTIC)
            put(
                "product_reference",
                f.after_label(r"R[ée]f[ée]rence\s*produit|produit", r"[A-Z]{2,}-[\w\-]+"),
                LABEL,
            )
            put(
                "serial_number",
                f.after_label(
                    r"N[°o*º]?\s*de\s*s[ée]rie|num[ée]ro\s*de\s*s[ée]rie", r"[A-Z0-9]{2,}-?[\w\-]*"
                ),
                LABEL,
            )
            d = f.after_label(r"Date\s*d'achat|achet[ée][^\n]*?\)\s*le", _DATE)
            put("purchase_date", parse_date(d) if d else None, LABEL)
            d = f.after_label(r"Date\s*de\s*la\s*panne|Depuis\s*le", _DATE)
            put("failure_date", parse_date(d) if d else None, LABEL)
            put("invoice_number", f.after_label(r"facture\s*d'achat|facture", r"F-\d{4}-\d+"), LABEL)
            desc = f.line_after("Description de la panne") or f.after_label(
                r"probl[èe]me\s*suivant", r"[^\n]+"
            )
            if desc:
                put("failure_description", desc[0].upper() + desc[1:], LABEL)

        if ocr_confidence is not None:  # un texte lu par OCR est moins sûr
            factor = min(1.0, ocr_confidence + 0.1)
            conf = {k: round(v * factor, 2) for k, v in conf.items()}
        try:
            data = validate_fields(doc_type, raw)
        except ValidationError as exc:
            raise ExtractionError(f"Valeurs extraites invalides : {exc.error_count()} erreur(s).") from exc
        for spec in FIELDS[doc_type]:
            conf.setdefault(spec.name, 0.0)
        return ExtractionResult(data=data, confidence=conf, provider=self.name)
