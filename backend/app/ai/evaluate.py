"""Évaluation du classificateur de demandes sur un jeu étiqueté (US-203).

    python -m app.ai.evaluate                  # mode démonstration, split test
    python -m app.ai.evaluate --split all
    AI_PROVIDER=claude ANTHROPIC_API_KEY=... python -m app.ai.evaluate --provider claude

Le jeu (app/ai/eval/triage_dataset.jsonl) est synthétique et étiqueté selon les règles de gestion.
Split « dev » : exemples consultés pendant l'écriture des règles. Split « test » : non utilisés pour
les ajuster. Les deux ont été rédigés par la même personne que les règles : voir les limites dans
docs/07-ai-governance/triage-evaluation.md.
"""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

from app.ai.triage import CategoryOption, TeamOption, TriageError, TriageInput, TriageProvider
from app.demo_catalog import CATEGORIES
from app.modules.requests.schemas import ConfusionCell, EvaluationReport, FieldScore

DATASET = Path(__file__).parent / "eval" / "triage_dataset.jsonl"
TEAMS = [TeamOption(code, code) for code in sorted({c[3] for c in CATEGORIES})]
OPTIONS = [CategoryOption(code, name, desc, team) for code, name, desc, team in CATEGORIES]
DEFAULT_TEAM = {code: team for code, _, _, team in CATEGORIES}


def load(split: str) -> list[dict[str, str]]:
    rows = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows if split == "all" else [r for r in rows if r["split"] == split]


def evaluate(provider: TriageProvider, split: str = "test") -> EvaluationReport:
    rows = load(split)
    correct: Counter[str] = Counter()
    confusion: Counter[tuple[str, str]] = Counter()
    errors: list[dict[str, str]] = []
    latencies: list[float] = []
    all_three = 0
    for row in rows:
        item = TriageInput(row["title"], row["description"], row["channel"], row["tier"])
        started = time.perf_counter()
        try:
            p = provider.suggest(item, OPTIONS, TEAMS)
        except TriageError as exc:
            errors.append({"id": row["id"], "error": str(exc)})
            continue
        latencies.append((time.perf_counter() - started) * 1000)
        expected_team = DEFAULT_TEAM[row["category"]]
        hits = {
            "category": p.category_code == row["category"],
            "priority": p.priority == row["priority"],
            "team": p.team_code == expected_team,
        }
        correct.update(k for k, ok in hits.items() if ok)
        all_three += all(hits.values())
        confusion[(row["category"], p.category_code)] += 1
        if not all(hits.values()):
            errors.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "expected": f"{row['category']} / {row['priority']}",
                    "predicted": f"{p.category_code} / {p.priority}",
                }
            )
    n = len(rows)
    return EvaluationReport(
        provider=provider.name,
        dataset=DATASET.name,
        split=split,
        size=n,
        fields=[
            FieldScore(field=f, correct=correct[f], total=n, accuracy=round(correct[f] / n, 3) if n else 0.0)
            for f in ("category", "priority", "team")
        ],
        all_three_correct=round(all_three / n, 3) if n else 0.0,
        mean_latency_ms=round(sum(latencies) / len(latencies), 1) if latencies else 0.0,
        category_confusion=[
            ConfusionCell(expected=e, predicted=p, count=c) for (e, p), c in sorted(confusion.items())
        ],
        errors=errors,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--split", choices=["dev", "test", "all"], default="test")
    parser.add_argument("--provider", choices=["mock", "claude"], default="mock")
    args = parser.parse_args()
    if args.provider == "claude":
        from app.ai import get_triage_provider

        provider = get_triage_provider()
        if not provider.name.startswith("claude"):
            print("AI_PROVIDER=claude et ANTHROPIC_API_KEY sont nécessaires.", file=sys.stderr)
            return 1
    else:
        from app.ai.triage import MockTriageProvider

        provider = MockTriageProvider()
    report = evaluate(provider, args.split)
    print(f"Fournisseur : {report.provider} — split {report.split} — {report.size} demandes\n")
    print("| Champ | Correct | Exactitude |\n|---|---|---|")
    for f in report.fields:
        print(f"| {f.field} | {f.correct}/{f.total} | {f.accuracy:.0%} |")
    print(f"| les trois | | {report.all_three_correct:.0%} |")
    print(f"\nLatence moyenne : {report.mean_latency_ms} ms")
    if report.errors:
        print("\nErreurs :")
        for e in report.errors:
            print(
                f"- {e['id']} {e.get('title', '')} : attendu {e.get('expected')}, obtenu {e.get('predicted')}"
                if "expected" in e
                else f"- {e['id']} : {e['error']}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
