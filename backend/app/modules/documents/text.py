"""Conversion PDF → texte (BR-06) : couche texte si elle existe, OCR Tesseract sinon.

Une page est considérée comme scannée quand sa couche texte contient moins de MIN_CHARS caractères
utiles. L'OCR rend la page en image à OCR_DPI et lit le français (`fra`).
"""

import shutil
from dataclasses import dataclass

import pypdfium2 as pdfium

MIN_CHARS = 25
OCR_DPI = 300
MAX_PAGES = 10


class TextExtractionError(Exception):
    """Le PDF ne peut pas être lu (fichier corrompu, protégé, OCR indisponible…)."""


@dataclass
class ExtractedText:
    text: str
    page_count: int
    ocr_pages: int
    ocr_confidence: float | None  # moyenne Tesseract (0 à 1) sur les pages OCR

    @property
    def ocr_used(self) -> bool:
        return self.ocr_pages > 0


def ocr_available() -> bool:
    return shutil.which("tesseract") is not None


def _ocr_page(page: pdfium.PdfPage) -> tuple[str, float | None]:
    import pytesseract

    image = page.render(scale=OCR_DPI / 72, grayscale=True).to_pil()
    data = pytesseract.image_to_data(image, lang="fra", output_type=pytesseract.Output.DICT)
    confs = [float(c) for c, w in zip(data["conf"], data["text"], strict=True) if w.strip() and float(c) >= 0]
    text = pytesseract.image_to_string(image, lang="fra")
    return text, (sum(confs) / len(confs) / 100 if confs else None)


def extract_text(pdf: bytes) -> ExtractedText:
    try:
        doc = pdfium.PdfDocument(pdf)
    except pdfium.PdfiumError as exc:
        raise TextExtractionError("PDF illisible ou protégé par mot de passe.") from exc
    try:
        if len(doc) == 0:
            raise TextExtractionError("Le PDF ne contient aucune page.")
        if len(doc) > MAX_PAGES:
            raise TextExtractionError(f"Document trop long ({len(doc)} pages, {MAX_PAGES} maximum).")
        parts: list[str] = []
        ocr_pages = 0
        confs: list[float] = []
        for page in doc:
            textpage = page.get_textpage()
            text = textpage.get_text_bounded()
            textpage.close()
            if len("".join(text.split())) < MIN_CHARS:
                if not ocr_available():
                    raise TextExtractionError(
                        "Document scanné : l'OCR (Tesseract) n'est pas installé sur ce serveur."
                    )
                text, conf = _ocr_page(page)
                ocr_pages += 1
                if conf is not None:
                    confs.append(conf)
            parts.append(text.replace("\r\n", "\n").replace("\r", "\n"))
        return ExtractedText(
            text="\n\f\n".join(p.strip() for p in parts),
            page_count=len(doc),
            ocr_pages=ocr_pages,
            ocr_confidence=round(sum(confs) / len(confs), 2) if confs else None,
        )
    finally:
        doc.close()
