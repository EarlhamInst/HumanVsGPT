"""Turning comparison results into artefacts a reader can check and act on.

Five outputs, each answering a different question:

* `summary.csv`      -- one row per paper: how did this pair score, and how much
                        did each side fill in?
* `structure.csv`    -- one row per sheet: did the shape survive?
* `fields.csv`        -- every field comparison, so any number can be traced back
                         to the two cell values that produced it.
* `adjudication.csv` -- only the fields that cannot be settled without the paper.
* `run.json`         -- what was run, over which bytes, with which constants.

`run.json` is what makes a published result reproducible. It records not just the
inputs and their hashes but every threshold the verdicts depend on, so a reader
who disagrees with a cut-off can see its value rather than infer it from source.
"""

from __future__ import annotations

import csv
import json
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .align import AMBIGUITY_MARGIN, LINK_BONUS, MATCH_THRESHOLD
from .compare import (
    NEEDS_ADJUDICATION,
    NUMERIC_RTOL,
    TEXT_DIVERGENT,
    TEXT_EQUIVALENT,
    TEXT_NEAR_IDENTICAL,
    Outcome,
    PairResult,
)
from .schema import CLASS_WEIGHTS, SHEET_WEIGHTS

#: Cell values are truncated in the CSVs so a stray paragraph of protocol prose
#: cannot make the file unreadable in a spreadsheet.
MAX_CELL = 300


def _clip(value: str) -> str:
    value = " ".join(str(value or "").split())
    return value if len(value) <= MAX_CELL else value[: MAX_CELL - 1] + "…"


def summary_rows(results: list[PairResult]) -> list[dict]:
    rows = []
    for result in results:
        counts = result.counts
        rows.append(
            {
                "paper": result.paper,
                "reference_file": Path(result.reference_provenance["path"]).name,
                "test_file": Path(result.test_provenance["path"]).name,
                "recall": round(result.recall, 4),
                "precision": round(result.precision, 4),
                "structural_fidelity": round(result.structural_fidelity, 4),
                "reference_filled": result.reference_filled,
                "test_filled": result.test_filled,
                "reference_fill_rate": round(result.reference_fill_rate, 4),
                "test_fill_rate": round(result.test_fill_rate, 4),
                "coverage_ratio": round(result.coverage_ratio, 3),
                "fields_compared": len(result.fields),
                "adjudication_needed": len(result.adjudication_queue),
                **{f"n_{k}": v for k, v in counts.items() if k != "both_absent"},
            }
        )
    return rows


def structure_rows(results: list[PairResult]) -> list[dict]:
    rows = []
    for result in results:
        for sheet in result.structure:
            if not (sheet.reference_rows or sheet.test_rows):
                continue
            rows.append(
                {
                    "paper": result.paper,
                    "sheet": sheet.sheet,
                    "reference_rows": sheet.reference_rows,
                    "test_rows": sheet.test_rows,
                    "reference_distinct": sheet.reference_distinct,
                    "test_distinct": sheet.test_distinct,
                    "matched": sheet.matched,
                    "ambiguous": sheet.ambiguous,
                    "cardinality_ok": sheet.cardinality_ok,
                    "sheet_missing_in_test": sheet.missing_in_test,
                    "coverage": round(sheet.coverage, 4),
                }
            )
    return rows


def field_rows(results: list[PairResult], only_adjudication: bool = False) -> list[dict]:
    rows = []
    for result in results:
        fields = result.adjudication_queue if only_adjudication else result.fields
        for item in fields:
            rows.append(
                {
                    "paper": result.paper,
                    "sheet": item.sheet,
                    "column": item.column,
                    "field_class": item.field_class.value,
                    "outcome": item.outcome.value,
                    "reference_value": _clip(item.reference),
                    "test_value": _clip(item.test),
                    "detail": item.detail,
                }
            )
    return rows


def corpus_totals(results: list[PairResult]) -> dict:
    """Corpus-level figures, reported two ways because they differ.

    The mean of per-paper scores weights every paper equally; pooling all fields
    weights every field equally and so lets one large manifest dominate. Both are
    defensible and they are not interchangeable, so both are reported.
    """
    if not results:
        return {}
    n = len(results)
    pooled: list = [f for r in results for f in r.fields]
    weighted = lambda fs, keep: sum(f.weight for f in fs if f.outcome in keep)
    captured = {Outcome.EXACT, Outcome.EQUIVALENT, Outcome.TEST_MORE_SPECIFIC}
    recall_den = weighted(
        pooled,
        captured | {Outcome.TEST_LESS_SPECIFIC, Outcome.CONFLICT, Outcome.MISSING_IN_TEST},
    )
    precision_den = weighted(
        pooled, captured | {Outcome.TEST_LESS_SPECIFIC, Outcome.CONFLICT}
    )
    return {
        "pairs": n,
        "mean_recall": round(sum(r.recall for r in results) / n, 4),
        "mean_precision": round(sum(r.precision for r in results) / n, 4),
        "mean_structural_fidelity": round(
            sum(r.structural_fidelity for r in results) / n, 4
        ),
        "pooled_recall": round(weighted(pooled, captured) / recall_den, 4)
        if recall_den
        else 0.0,
        "pooled_precision": round(weighted(pooled, captured) / precision_den, 4)
        if precision_den
        else 0.0,
        "fields_compared": len(pooled),
        "adjudication_needed": sum(len(r.adjudication_queue) for r in results),
        "reference_filled": sum(r.reference_filled for r in results),
        "test_filled": sum(r.test_filled for r in results),
        "coverage_ratio": round(
            sum(r.test_filled for r in results)
            / max(sum(r.reference_filled for r in results), 1),
            3,
        ),
        "mean_reference_fill_rate": round(
            sum(r.reference_fill_rate for r in results) / n, 4
        ),
        "mean_test_fill_rate": round(sum(r.test_fill_rate for r in results) / n, 4),
    }


def run_metadata(results: list[PairResult], argv: list[str] | None = None) -> dict:
    """Everything needed to reproduce this run, including the tuning constants."""
    return {
        "tool": "manifest-compare",
        "version": __version__,
        "run_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": " ".join(argv or sys.argv),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "parameters": {
            "align.MATCH_THRESHOLD": MATCH_THRESHOLD,
            "align.LINK_BONUS": LINK_BONUS,
            "align.AMBIGUITY_MARGIN": AMBIGUITY_MARGIN,
            "compare.NUMERIC_RTOL": NUMERIC_RTOL,
            "compare.TEXT_EQUIVALENT": TEXT_EQUIVALENT,
            "compare.TEXT_DIVERGENT": TEXT_DIVERGENT,
            "compare.TEXT_NEAR_IDENTICAL": TEXT_NEAR_IDENTICAL,
            "schema.CLASS_WEIGHTS": {k.value: v for k, v in CLASS_WEIGHTS.items()},
            "schema.SHEET_WEIGHTS": SHEET_WEIGHTS,
        },
        "totals": corpus_totals(results),
        "inputs": [
            {
                "paper": r.paper,
                "reference": r.reference_provenance,
                "test": r.test_provenance,
            }
            for r in results
        ],
    }


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_reports(
    results: list[PairResult], out_dir: str | Path, argv: list[str] | None = None
) -> dict[str, Path]:
    """Write every artefact and return where each landed."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = {
        "summary": out / "summary.csv",
        "structure": out / "structure.csv",
        "fields": out / "fields.csv",
        "adjudication": out / "adjudication.csv",
        "run": out / "run.json",
    }
    _write_csv(written["summary"], summary_rows(results))
    _write_csv(written["structure"], structure_rows(results))
    _write_csv(written["fields"], field_rows(results))
    _write_csv(written["adjudication"], field_rows(results, only_adjudication=True))
    written["run"].write_text(
        json.dumps(run_metadata(results, argv), indent=2), encoding="utf-8"
    )
    return written


# --- Human-readable scorecard ------------------------------------------------

def scorecard(result: PairResult) -> str:
    """A readable per-paper summary for the terminal."""
    lines = [
        f"{result.paper[:78]}",
        f"  reference : {Path(result.reference_provenance['path']).name}",
        f"  test      : {Path(result.test_provenance['path']).name}",
        f"  recall {result.recall:6.1%}   precision {result.precision:6.1%}"
        f"   structural {result.structural_fidelity:5.0%}",
        f"  filled    : reference {result.reference_filled} "
        f"({result.reference_fill_rate:.0%})   test {result.test_filled} "
        f"({result.test_fill_rate:.0%})   ratio {result.coverage_ratio:.2f}x",
    ]
    counts = {k: v for k, v in result.counts.items() if v and k != "both_absent"}
    lines.append("  outcomes  : " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    problems = [
        s for s in result.structure
        if (s.reference_rows or s.test_rows) and (not s.cardinality_ok or s.missing_in_test)
    ]
    for sheet in problems:
        note = "sheet absent" if sheet.missing_in_test else \
            f"{sheet.reference_rows} vs {sheet.test_rows} rows"
        lines.append(f"  structure : {sheet.sheet} -- {note}")
    if result.adjudication_queue:
        lines.append(f"  adjudicate: {len(result.adjudication_queue)} fields")
    return "\n".join(lines)


def corpus_report(results: list[PairResult]) -> str:
    """A ranked table plus corpus totals."""
    totals = corpus_totals(results)
    lines = [
        f"{'recall':>7} {'prec':>7} {'struct':>7} {'ref':>6} {'test':>6} {'x':>6}  paper",
        "-" * 92,
    ]
    for result in sorted(results, key=lambda r: -r.recall):
        lines.append(
            f"{result.recall:7.1%} {result.precision:7.1%} "
            f"{result.structural_fidelity:7.0%} "
            f"{result.reference_filled:6d} {result.test_filled:6d} "
            f"{result.coverage_ratio:5.2f}x  {result.paper[:40]}"
        )
    lines += [
        "-" * 92,
        f"{len(results)} pairs | mean recall {totals['mean_recall']:.1%} | "
        f"mean precision {totals['mean_precision']:.1%} | "
        f"mean structural {totals['mean_structural_fidelity']:.0%}",
        f"pooled recall {totals['pooled_recall']:.1%} | "
        f"pooled precision {totals['pooled_precision']:.1%} | "
        f"{totals['fields_compared']} fields compared | "
        f"{totals['adjudication_needed']} need adjudication",
        f"coverage: reference filled {totals['reference_filled']} fields, "
        f"test filled {totals['test_filled']} ({totals['coverage_ratio']:.2f}x). "
        "Coverage is descriptive only -- neither manifest is validated, so a "
        "fuller one is not thereby a better one.",
    ]
    return "\n".join(lines)
