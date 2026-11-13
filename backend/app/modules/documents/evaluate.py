"""Évaluation de l'extraction documentaire sur le jeu étiqueté (mesure par champ).

    python -m app.modules.documents.evaluate                 # mode démonstration, split test
    python -m app.modules.documents.evaluate --split dev
    AI_PROVIDER=claude ANTHROPIC_API_KEY=... python -m app.modules.documents.evaluate --provider claude

Chaque PDF est fabriqué à partir de ses valeurs attendues (eval/render.py), puis passe par la même
chaîne que l'application : texte (OCR si scanné), extraction, contrôles. Sans Tesseract, les scans
sont comptés à part (« non évalués ») au lieu d'être comptés faux. Les règles du mode
démonstration n'ont été écrites qu'à partir du split dev.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from app.modules.documents import controls
from app.modules.documents.eval.render import render
from app.modules.documents.extract import DocumentExtractor, ExtractionError
from app.modules.documents.fields import FIELDS, DocType
from app.modules.documents.schemas import AnomalyScore, ExtractionReport, FieldScore
from app.modules.documents.text import TextExtractionError, extract_text

DATASET = Path(__file__).parent / "eval" / "documents_dataset.jsonl"
EVAL_TODAY = date(2026, 11, 13)  # date figée : les contrôles de dates restent reproductibles
CHECKED_ANOMALIES = {
    "INCONSISTENT_TOTAL",
    "DUE_BEFORE_INVOICE",
    "DUPLICATE",
    "FAILURE_BEFORE_PURCHASE",
    "OUT_OF_WARRANTY",
    "MISSING_FIELD",
}


def load(split: str) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows if split == "all" else [r for r in rows if r["split"] == split]


def same(kind: str, expected: Any, got: Any) -> bool:
    """Égalité métier : casse et espaces ignorés pour le texte, au centime près pour les montants."""
    if expected is None or got is None:
        return expected is None and got is None
    if kind == "amount":
        return abs(float(expected) - float(got)) <= 0.01
    if kind == "text":
        return " ".join(str(expected).casefold().split()) == " ".join(str(got).casefold().split())
    return str(expected) == str(got)


def evaluate(extractor: DocumentExtractor, split: str = "test") -> ExtractionReport:
    rows = load(split)
    correct: Counter[str] = Counter()
    totals: Counter[str] = Counter()
    labels: dict[str, str] = {}
    by_layout: dict[str, list[bool]] = defaultdict(list)
    text_hits: list[bool] = []
    scan_hits: list[bool] = []
    errors: list[dict[str, str]] = []
    full = evaluated = skipped = 0
    seen_keys: dict[str, str] = {}
    expected_anomalies = detected = false_alarms = 0

    for row in rows:
        doc_type: DocType = row["doc_type"]
        try:
            text = extract_text(render(row))
        except TextExtractionError as exc:
            if row["scanned"]:
                skipped += 1
                continue
            errors.append({"id": row["id"], "error": str(exc)})
            continue
        try:
            result = extractor.extract(doc_type, text.text, text.ocr_confidence)
        except ExtractionError as exc:
            errors.append({"id": row["id"], "error": str(exc)})
            continue
        evaluated += 1
        wrong = []
        for f in FIELDS[doc_type]:
            key = f"{doc_type}.{f.name}"
            labels[key] = f.label
            ok = same(f.kind, row["expected"][f.name], result.data.get(f.name))
            totals[key] += 1
            correct[key] += ok
            (scan_hits if row["scanned"] else text_hits).append(ok)
            by_layout[f"{row['layout']}{' (scan)' if row['scanned'] else ''}"].append(ok)
            if not ok:
                wrong.append(
                    f"{f.name}: attendu {row['expected'][f.name]!r}, obtenu {result.data.get(f.name)!r}"
                )
        full += not wrong
        if wrong:
            errors.append(
                {
                    "id": row["id"],
                    "layout": row["layout"],
                    "scanned": str(row["scanned"]),
                    "fields": " ; ".join(wrong),
                }
            )

        # Contrôles sur les valeurs extraites, comme dans l'application (doublons dans l'ordre d'arrivée)
        dup_key = controls.duplicate_key(doc_type, result.data)
        dups = [seen_keys[dup_key]] if dup_key and dup_key in seen_keys else []
        if dup_key and dup_key not in seen_keys:
            seen_keys[dup_key] = row["id"]
        found = {f.code for f in controls.check(doc_type, result.data, EVAL_TODAY, dups)} & CHECKED_ANOMALIES
        expected = set(row["expected_anomalies"])
        expected_anomalies += len(expected)
        detected += len(expected & found)
        false_alarms += len(found - expected)

    def rate(xs: list[bool]) -> float | None:
        return round(sum(xs) / len(xs), 3) if xs else None

    return ExtractionReport(
        provider=extractor.name,
        split=split,
        size=len(rows),
        evaluated=evaluated,
        skipped_scans=skipped,
        fields=[
            FieldScore(
                field=k,
                label=labels[k],
                correct=correct[k],
                total=totals[k],
                accuracy=round(correct[k] / totals[k], 3),
            )
            for k in totals
        ],
        documents_fully_correct=round(full / evaluated, 3) if evaluated else 0.0,
        text_accuracy=rate(text_hits),
        scan_accuracy=rate(scan_hits),
        by_layout={k: round(sum(v) / len(v), 3) for k, v in sorted(by_layout.items())},
        anomalies=AnomalyScore(expected=expected_anomalies, detected=detected, false_alarms=false_alarms),
        errors=errors,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--split", choices=["dev", "test", "all"], default="test")
    parser.add_argument("--provider", choices=["mock", "claude"], default="mock")
    args = parser.parse_args()
    if args.provider == "claude":
        from app.ai import get_document_extractor

        extractor = get_document_extractor()
        if not extractor.name.startswith("claude"):
            print("AI_PROVIDER=claude et ANTHROPIC_API_KEY sont nécessaires.", file=sys.stderr)
            return 1
    else:
        from app.modules.documents.extract import MockDocumentExtractor

        extractor = MockDocumentExtractor()
    r = evaluate(extractor, args.split)
    print(f"Fournisseur : {r.provider} — split {r.split} — {r.evaluated}/{r.size} documents évalués")
    if r.skipped_scans:
        print(f"{r.skipped_scans} scans non évalués : Tesseract absent sur cette machine.")
    print("\n| Champ | Correct | Exactitude |\n|---|---|---|")
    for f in r.fields:
        print(f"| {f.field} | {f.correct}/{f.total} | {f.accuracy:.0%} |")
    print(f"\nDocuments entièrement justes : {r.documents_fully_correct:.0%}")
    print(f"Exactitude par champ — PDF texte : {r.text_accuracy}, scans : {r.scan_accuracy}")
    print(f"Par mise en page : {r.by_layout}")
    a = r.anomalies
    print(f"Anomalies attendues : {a.expected}, détectées : {a.detected}, fausses alertes : {a.false_alarms}")
    for e in r.errors:
        print("-", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
