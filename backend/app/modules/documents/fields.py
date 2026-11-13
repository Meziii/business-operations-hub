"""Champs extraits par type de document (BR-07) : définition, libellés et validation.

Les valeurs sont stockées en JSON : texte, date ISO (AAAA-MM-JJ) ou montant (nombre à 2 décimales).
Un champ absent vaut None. La validation Pydantic garantit le format avant tout enregistrement.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

DocType = Literal["INVOICE", "WARRANTY_CLAIM"]
FieldKind = Literal["text", "date", "amount"]


@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    kind: FieldKind
    required: bool


FIELDS: dict[DocType, list[FieldSpec]] = {
    "INVOICE": [
        FieldSpec("invoice_number", "Numéro de facture", "text", True),
        FieldSpec("invoice_date", "Date de facture", "date", True),
        FieldSpec("due_date", "Date d'échéance", "date", False),
        FieldSpec("supplier_name", "Émetteur", "text", True),
        FieldSpec("customer_name", "Client facturé", "text", True),
        FieldSpec("order_reference", "Référence de commande", "text", False),
        FieldSpec("total_excl_tax", "Total HT", "amount", True),
        FieldSpec("vat_amount", "TVA", "amount", True),
        FieldSpec("total_incl_tax", "Total TTC", "amount", True),
    ],
    "WARRANTY_CLAIM": [
        FieldSpec("customer_name", "Client", "text", True),
        FieldSpec("product_reference", "Référence produit", "text", True),
        FieldSpec("serial_number", "Numéro de série", "text", True),
        FieldSpec("purchase_date", "Date d'achat", "date", True),
        FieldSpec("failure_date", "Date de la panne", "date", True),
        FieldSpec("invoice_number", "Facture d'achat", "text", False),
        FieldSpec("failure_description", "Description de la panne", "text", True),
    ],
}

DOC_TYPE_LABELS: dict[DocType, str] = {"INVOICE": "Facture", "WARRANTY_CLAIM": "Demande de garantie"}


def as_doc_type(value: str) -> DocType:
    """Convertit la valeur stockée (enum de la base) en type de document connu."""
    if value == "INVOICE":
        return "INVOICE"
    if value == "WARRANTY_CLAIM":
        return "WARRANTY_CLAIM"
    raise ValueError(f"Type de document inconnu : {value}")


def spec(doc_type: DocType, name: str) -> FieldSpec:
    return next(f for f in FIELDS[doc_type] if f.name == name)


class _Fields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def _blank_is_none(cls, v: Any) -> Any:
        return None if isinstance(v, str) and not v.strip() else v.strip() if isinstance(v, str) else v


class InvoiceFields(_Fields):
    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    supplier_name: str | None = None
    customer_name: str | None = None
    order_reference: str | None = None
    total_excl_tax: float | None = None
    vat_amount: float | None = None
    total_incl_tax: float | None = None


class WarrantyFields(_Fields):
    customer_name: str | None = None
    product_reference: str | None = None
    serial_number: str | None = None
    purchase_date: date | None = None
    failure_date: date | None = None
    invoice_number: str | None = None
    failure_description: str | None = None


MODELS: dict[DocType, type[_Fields]] = {"INVOICE": InvoiceFields, "WARRANTY_CLAIM": WarrantyFields}


def validate_fields(doc_type: DocType, data: dict[str, Any]) -> dict[str, Any]:
    """Valide et normalise : dates ISO, montants arrondis à 2 décimales. Lève ValidationError."""
    model = MODELS[doc_type].model_validate(data)
    out = model.model_dump(mode="json")
    for f in FIELDS[doc_type]:
        if f.kind == "amount" and out[f.name] is not None:
            out[f.name] = round(float(out[f.name]), 2)
    return out
