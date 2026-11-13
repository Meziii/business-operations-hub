"""Contrôles d'une extraction (BR-08, règles RC-01 à RC-09 de docs/03-processes/document-processing.md).

Fonctions pures : elles reçoivent les valeurs et, pour le doublon, les références des documents
déjà enregistrés qui portent la même clé. Une anomalie bloquante empêche la validation.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from app.modules.documents.fields import FIELDS, DocType, spec

Severity = Literal["BLOCKING", "WARNING"]

AMOUNT_TOLERANCE = 0.02  # arrondis
VAT_RATES = (0.0, 0.021, 0.055, 0.10, 0.20)  # taux français en vigueur
VAT_RATE_TOLERANCE = 0.002
WARRANTY_MONTHS = 24


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str
    field: str | None = None


def _d(v: Any) -> date | None:
    return date.fromisoformat(v) if isinstance(v, str) else None


def _months_between(a: date, b: date) -> float:
    return (b.year - a.year) * 12 + (b.month - a.month) + (b.day - a.day) / 31


def duplicate_key(doc_type: DocType, data: dict[str, Any]) -> str | None:
    """Clé de doublon (RC-05) : émetteur + numéro pour une facture, n° de série + date de panne sinon."""

    def norm(v: Any) -> str:
        return " ".join(str(v).casefold().split())

    if doc_type == "INVOICE" and data.get("invoice_number") and data.get("supplier_name"):
        return f"INVOICE|{norm(data['supplier_name'])}|{norm(data['invoice_number'])}"
    if doc_type == "WARRANTY_CLAIM" and data.get("serial_number") and data.get("failure_date"):
        return f"WARRANTY|{norm(data['serial_number'])}|{data['failure_date']}"
    return None


def check(
    doc_type: DocType, data: dict[str, Any], today: date, duplicates_of: list[str] | None = None
) -> list[Finding]:
    out: list[Finding] = []

    # RC-01 : champs obligatoires
    for f in FIELDS[doc_type]:
        if f.required and data.get(f.name) in (None, ""):
            out.append(Finding("MISSING_FIELD", "BLOCKING", f"{f.label} manquant.", f.name))

    # RC-05 : doublon
    if duplicates_of:
        out.append(
            Finding(
                "DUPLICATE",
                "BLOCKING",
                f"Doublon probable de {', '.join(duplicates_of)}.",
                "invoice_number" if doc_type == "INVOICE" else "serial_number",
            )
        )

    # RC-09 : date dans le futur
    for f in FIELDS[doc_type]:
        if f.kind == "date" and f.name != "due_date" and (d := _d(data.get(f.name))) and d > today:
            out.append(Finding("DATE_IN_FUTURE", "WARNING", f"{f.label} postérieure à aujourd'hui.", f.name))

    if doc_type == "INVOICE":
        ht, vat, ttc = data.get("total_excl_tax"), data.get("vat_amount"), data.get("total_incl_tax")
        # RC-02 : HT + TVA = TTC
        if ht is not None and vat is not None and ttc is not None and abs(ht + vat - ttc) > AMOUNT_TOLERANCE:
            out.append(
                Finding(
                    "INCONSISTENT_TOTAL",
                    "BLOCKING",
                    f"HT + TVA = {ht + vat:.2f}, mais le total TTC indiqué est {ttc:.2f}.",
                    "total_incl_tax",
                )
            )
        # RC-04 : taux de TVA usuel
        if ht and vat is not None and ht > 0:
            rate = vat / ht
            if all(abs(rate - r) > VAT_RATE_TOLERANCE for r in VAT_RATES):
                out.append(
                    Finding(
                        "UNUSUAL_VAT_RATE", "WARNING", f"Taux de TVA inhabituel ({rate:.1%}).", "vat_amount"
                    )
                )
        # RC-03 : échéance après la date de facture
        inv, due = _d(data.get("invoice_date")), _d(data.get("due_date"))
        if inv and due and due < inv:
            out.append(
                Finding(
                    "DUE_BEFORE_INVOICE", "WARNING", "Échéance antérieure à la date de facture.", "due_date"
                )
            )
    else:
        bought, failed = _d(data.get("purchase_date")), _d(data.get("failure_date"))
        if bought and failed:
            # RC-06 : panne après l'achat
            if failed < bought:
                out.append(
                    Finding(
                        "FAILURE_BEFORE_PURCHASE",
                        "BLOCKING",
                        "La panne est datée avant l'achat.",
                        "failure_date",
                    )
                )
            # RC-07 : période de garantie
            elif _months_between(bought, failed) > WARRANTY_MONTHS:
                out.append(
                    Finding(
                        "OUT_OF_WARRANTY",
                        "WARNING",
                        f"Panne plus de {WARRANTY_MONTHS} mois après l'achat : hors garantie standard.",
                        "failure_date",
                    )
                )
    return out


def field_label(doc_type: DocType, name: str | None) -> str | None:
    return spec(doc_type, name).label if name else None
