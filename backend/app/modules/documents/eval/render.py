"""Fabrique les PDF synthétiques du jeu documentaire à partir des valeurs attendues.

Rendu déterministe : un même enregistrement donne toujours le même PDF. Les « scans » sont des
images du PDF texte, légèrement inclinées et bruitées : le système doit alors passer par l'OCR.
Mises en page : factures A (classique), B (texte libre), C (anglaise, jamais vue en mise au point) ;
garanties F (formulaire), L (courrier).
"""

import io
import random
from datetime import date
from typing import Any

from fpdf import FPDF

MONTHS = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]
ITEMS = [
    "Kit de maintenance standard",
    "Pièce de rechange référencée",
    "Prestation d'intervention sur site",
    "Lot de consommables",
    "Module électronique de commande",
    "Forfait de transport",
]


def _fr_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return d.strftime("%d/%m/%Y")


def _long_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def _fr_amount(x: float, thousands: str = " ") -> str:
    whole, dec = f"{x:.2f}".split(".")
    groups = f"{int(whole):,}".replace(",", thousands)
    return f"{groups},{dec}"


def _en_amount(x: float) -> str:
    return f"{x:,.2f}"


def _lines(total: float, rng: random.Random) -> list[tuple[str, int, float, float]]:
    """Découpe un total HT en 1 à 3 lignes dont la somme tombe juste."""
    n = rng.randint(1, 3)
    cents = round(total * 100)
    cuts = sorted(rng.sample(range(1, cents), n - 1)) if n > 1 and cents > n else []
    parts = [b - a for a, b in zip([0, *cuts], [*cuts, cents], strict=True)]
    out = []
    for part in parts:
        qty = rng.choice([1, 1, 2, 4]) if part % 4 == 0 else 1
        amount = part / 100
        out.append((rng.choice(ITEMS), qty, round(amount / qty, 2), amount))
    return out


class _Doc(FPDF):
    def __init__(self) -> None:
        super().__init__(format="A4")
        self.set_auto_page_break(auto=True, margin=15)
        self.set_creator("Business Operations Hub - données synthétiques")
        self.add_page()
        self.set_font("helvetica", size=10)

    def text_line(self, text: str, size: float = 10, style: str = "", h: float = 6) -> None:
        self.set_font("helvetica", style=style, size=size)
        self.multi_cell(0, h, text, new_x="LMARGIN", new_y="NEXT")


def _invoice_a(e: dict[str, Any], rate: float, rng: random.Random, pdf: _Doc) -> None:
    pdf.text_line(e["supplier_name"], 15, "B", 8)
    pdf.text_line("12 rue des Artisans - 69000 Lyon - SIRET 000 000 000 00000", 8)
    pdf.ln(6)
    pdf.text_line("FACTURE", 18, "B", 10)
    pdf.text_line(f"N° de facture : {e['invoice_number']}")
    pdf.text_line(f"Date : {_fr_date(e['invoice_date'])}")
    if e["due_date"]:
        pdf.text_line(f"Échéance : {_fr_date(e['due_date'])}")
    pdf.ln(3)
    pdf.text_line(f"Client : {e['customer_name']}", style="B")
    if e["order_reference"]:
        pdf.text_line(f"Votre commande : {e['order_reference']}")
    pdf.ln(5)
    pdf.set_font("helvetica", "B", 9)
    for w, t in ((95, "Désignation"), (20, "Qté"), (35, "PU HT"), (35, "Montant HT")):
        pdf.cell(w, 7, t, border=1)
    pdf.ln()
    pdf.set_font("helvetica", "", 9)
    for label, qty, pu, amount in _lines(e["total_excl_tax"], rng):
        pdf.cell(95, 7, label, border=1)
        pdf.cell(20, 7, str(qty), border=1)
        pdf.cell(35, 7, _fr_amount(pu), border=1)
        pdf.cell(35, 7, _fr_amount(amount), border=1)
        pdf.ln()
    pdf.ln(5)
    pct = f"{rate * 100:g}".replace(".", ",")
    for label, value in (
        ("Total HT", e["total_excl_tax"]),
        (f"TVA {pct} %", e["vat_amount"]),
        ("Total TTC", e["total_incl_tax"]),
    ):
        pdf.cell(150, 7, label, align="R")
        pdf.cell(35, 7, f"{_fr_amount(value)} EUR", align="R")
        pdf.ln()


def _invoice_b(e: dict[str, Any], rate: float, rng: random.Random, pdf: _Doc) -> None:
    pdf.text_line(e["supplier_name"].upper(), 13, "B", 7)
    pdf.ln(4)
    pdf.text_line(f"Facture n°{e['invoice_number']} du {_long_date(e['invoice_date'])}", 13, "B", 8)
    pdf.ln(3)
    pdf.text_line("Destinataire", 9, "B")
    pdf.text_line(e["customer_name"])
    pdf.text_line("Service comptabilité fournisseurs", 9)
    if e["order_reference"]:
        pdf.ln(2)
        pdf.text_line(f"Réf. commande client : {e['order_reference']}", 9)
    pdf.ln(4)
    for label, _qty, _pu, amount in _lines(e["total_excl_tax"], rng):
        pdf.text_line(f"- {label} : {_fr_amount(amount, '')} EUR", 9)
    pdf.ln(4)
    pct = f"{rate * 100:.1f}".replace(".", ",")
    pdf.text_line(f"Montant HT : {_fr_amount(e['total_excl_tax'], '')} EUR")
    pdf.text_line(f"TVA ({pct} %) : {_fr_amount(e['vat_amount'], '')} EUR")
    pdf.text_line(f"Net à payer : {_fr_amount(e['total_incl_tax'], '')} EUR", style="B")
    pdf.ln(4)
    if e["due_date"]:
        pdf.text_line(f"À régler avant le {_fr_date(e['due_date'])} par virement.", 9)
    else:
        pdf.text_line("Règlement par virement à réception.", 9)


def _invoice_c(e: dict[str, Any], rate: float, rng: random.Random, pdf: _Doc) -> None:
    pdf.text_line(e["supplier_name"], 14, "B", 8)
    pdf.text_line("Export department", 8)
    pdf.ln(5)
    pdf.text_line("INVOICE", 18, "B", 10)
    pdf.text_line(f"Invoice No.: {e['invoice_number']}")
    pdf.text_line(f"Issue date: {e['invoice_date']}")
    if e["due_date"]:
        pdf.text_line(f"Payment due: {e['due_date']}")
    pdf.ln(3)
    pdf.text_line(f"Bill to: {e['customer_name']}", style="B")
    if e["order_reference"]:
        pdf.text_line(f"PO number: {e['order_reference']}")
    pdf.ln(4)
    for label, qty, _pu, amount in _lines(e["total_excl_tax"], rng):
        pdf.text_line(f"{qty} x {label}    {_en_amount(amount)}", 9)
    pdf.ln(4)
    pdf.text_line(f"Subtotal: {_en_amount(e['total_excl_tax'])}")
    pdf.text_line(f"VAT {rate * 100:g}%: {_en_amount(e['vat_amount'])}")
    pdf.text_line(f"Total due: EUR {_en_amount(e['total_incl_tax'])}", style="B")


def _warranty_form(e: dict[str, Any], rng: random.Random, pdf: _Doc) -> None:
    pdf.text_line("DEMANDE DE PRISE EN CHARGE SOUS GARANTIE", 14, "B", 8)
    pdf.text_line("Formulaire à retourner au service après-vente", 8)
    pdf.ln(6)
    rows = [
        ("Client", e["customer_name"]),
        ("Référence produit", e["product_reference"]),
        ("N° de série", e["serial_number"]),
        ("Date d'achat", _fr_date(e["purchase_date"]) if e["purchase_date"] else None),
        ("Date de la panne", _fr_date(e["failure_date"]) if e["failure_date"] else None),
        ("N° de facture d'achat", e["invoice_number"]),
    ]
    for label, value in rows:
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(60, 8, f"{label} :")
        pdf.set_font("helvetica", "", 10)
        pdf.cell(0, 8, value or "", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.text_line("Description de la panne :", style="B")
    pdf.text_line(e["failure_description"])
    pdf.ln(8)
    pdf.text_line("Signature du client : ______________________", 9)


def _warranty_letter(e: dict[str, Any], rng: random.Random, pdf: _Doc) -> None:
    pdf.text_line(e["customer_name"], 12, "B", 7)
    pdf.text_line("Service technique", 9)
    pdf.ln(8)
    pdf.text_line(f"Le {_long_date(e['failure_date'])}", 10)
    pdf.ln(3)
    pdf.text_line("Objet : demande de garantie", style="B")
    pdf.ln(3)
    invoice = f", facture {e['invoice_number']}" if e["invoice_number"] else ""
    desc = e["failure_description"][0].lower() + e["failure_description"][1:]
    pdf.text_line(
        "Madame, Monsieur,\n\n"
        f"Nous avons acheté le produit {e['product_reference']} (numéro de série {e['serial_number']}) "
        f"le {_long_date(e['purchase_date'])}{invoice}. "
        f"Depuis le {_long_date(e['failure_date'])}, nous constatons le problème suivant : {desc}\n\n"
        "Nous vous remercions de bien vouloir prendre en charge ce produit au titre de la garantie.\n\n"
        f"Cordialement,\nLe service technique de {e['customer_name']}"
    )


def render_text_pdf(row: dict[str, Any]) -> bytes:
    rng = random.Random(row["id"])
    pdf = _Doc()
    e = row["expected"]
    layout = row["layout"]
    if row["doc_type"] == "INVOICE":
        {"A": _invoice_a, "B": _invoice_b, "C": _invoice_c}[layout](e, row["vat_rate"], rng, pdf)
    else:
        {"F": _warranty_form, "L": _warranty_letter}[layout](e, rng, pdf)
    return bytes(pdf.output())


def render_scan(pdf_bytes: bytes, seed: str, dpi: int = 200) -> bytes:
    """Transforme un PDF texte en PDF image (sans couche texte), comme un document scanné."""
    import pypdfium2 as pdfium
    from PIL import Image, ImageFilter

    rng = random.Random(f"scan-{seed}")
    doc = pdfium.PdfDocument(pdf_bytes)
    pages = []
    for page in doc:
        img = page.render(scale=dpi / 72, grayscale=True).to_pil().convert("L")
        img = img.rotate(
            rng.uniform(-1.2, 1.2), expand=False, fillcolor=255, resample=Image.Resampling.BICUBIC
        )
        img = img.filter(ImageFilter.GaussianBlur(0.6))
        px = img.load()
        assert px is not None
        w, h = img.size
        for _ in range(w * h // 400):  # poussières
            x, y = rng.randrange(w), rng.randrange(h)
            px[x, y] = rng.choice((0, 90, 160))
        pages.append(img)
    doc.close()
    out = io.BytesIO()
    pages[0].save(out, "PDF", resolution=dpi, save_all=True, append_images=pages[1:], quality=70)
    return out.getvalue()


def render(row: dict[str, Any]) -> bytes:
    pdf = render_text_pdf(row)
    return render_scan(pdf, row["id"]) if row["scanned"] else pdf
