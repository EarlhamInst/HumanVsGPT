"""Command-line entry point.

Two ways in. `compare` scores a whole corpus described by a pairing CSV; `pair`
scores two files directly, which is the quick way to inspect one paper while
tuning. Both write the same artefacts.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from . import __version__
from .adjudication import (
    Verdict,
    Verdicts,
    append_verdict,
    adjudicate,
    adjudication_summary,
    build_worksheet,
)
from .compare import PairResult, compare_manifests
from .io import load_manifest
from .report import corpus_report, scorecard, write_reports

#: Excel writes these lock files beside an open workbook; they are not manifests.
LOCK_PREFIX = "~$"

#: Header written when the worksheet is empty, so the file is still readable.
WORKSHEET_COLUMNS = [
    "paper", "sheet", "column", "field_class",
    "reference_value", "test_value",
    "reference_grounding", "test_grounding", "reference_missing_terms",
    "paper_evidence", "occurrences", "verdict", "note",
]


def _read_pairs(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"human_file", "gpt_file"}
    if rows and not required.issubset(rows[0]):
        raise SystemExit(
            f"{path}: expected columns {sorted(required)}, found {sorted(rows[0])}"
        )
    return [r for r in rows if not r["human_file"].startswith(LOCK_PREFIX)]


def _score_pair(
    reference_path: Path, test_path: Path, paper: str = ""
) -> PairResult:
    reference = load_manifest(reference_path, "reference")
    test = load_manifest(test_path, "test")
    return compare_manifests(reference, test, paper)


def cmd_compare(args: argparse.Namespace) -> int:
    pairs_csv = Path(args.pairs)
    root = pairs_csv.parent
    reference_dir = Path(args.reference_dir) if args.reference_dir else root / "human"
    test_dir = Path(args.test_dir) if args.test_dir else root / "gpt"

    results: list[PairResult] = []
    for row in _read_pairs(pairs_csv):
        reference_path = reference_dir / row["human_file"]
        test_path = test_dir / row["gpt_file"]
        for path in (reference_path, test_path):
            if not path.exists():
                raise SystemExit(f"missing input: {path}")
        results.append(
            _score_pair(reference_path, test_path, row.get("paper_title", ""))
        )
        if args.verbose:
            print(scorecard(results[-1]), file=sys.stderr)

    if not results:
        raise SystemExit(f"{pairs_csv}: no pairs to compare")

    print(corpus_report(results))
    written = write_reports(results, args.out, sys.argv)
    print(f"\nwrote {len(written)} artefacts to {Path(args.out).resolve()}")
    for name, path in written.items():
        print(f"  {name:13s} {path.name}")
    return 0


def cmd_pair(args: argparse.Namespace) -> int:
    result = _score_pair(Path(args.reference), Path(args.test), args.paper)
    print(scorecard(result))
    if args.out:
        written = write_reports([result], args.out, sys.argv)
        print(f"\nwrote artefacts to {Path(args.out).resolve()}")
        for name, path in written.items():
            print(f"  {name:13s} {path.name}")
    return 0


def _load_papers(pairs_csv: Path, pdf_dir: Path, cache: Path) -> dict:
    """Load the PDF text for every paper named in the pairing CSV."""
    from .grounding import PaperText

    mapping_path = pairs_csv.parent / "paper_pdfs.csv"
    if not mapping_path.exists():
        raise SystemExit(
            f"{mapping_path} not found; it maps paper_title -> pdf_file"
        )
    papers = {}
    with mapping_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            pdf = pdf_dir / row["pdf_file"]
            if pdf.exists():
                papers[row["paper_title"]] = PaperText.from_pdf(pdf, cache_dir=cache)
    return papers


def cmd_adjudicate(args: argparse.Namespace) -> int:
    pairs_csv = Path(args.pairs)
    root = pairs_csv.parent
    results = [
        _score_pair(
            root / "human" / row["human_file"],
            root / "gpt" / row["gpt_file"],
            row.get("paper_title", ""),
        )
        for row in _read_pairs(pairs_csv)
    ]
    verdicts = Verdicts.load(args.decisions)
    decided = adjudicate(results, verdicts)
    summary = adjudication_summary(decided)
    total = len(decided)
    print(f"{total} conflicts; {len(verdicts.rulings)} rulings, "
          f"{len(verdicts.items)} item verdicts on file")
    for name, count in sorted(summary.items(), key=lambda kv: -kv[1]):
        print(f"   {name:12s} {count:5d}  {count / total:6.1%}")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "adjudicated.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(decided[0]))
        writer.writeheader()
        writer.writerows(decided)

    papers = {}
    if args.pdf_dir:
        papers = _load_papers(pairs_csv, Path(args.pdf_dir), Path(args.cache))
    worksheet = build_worksheet(
        results, papers, verdicts, only_test_grounded=args.test_grounded_only
    )
    # Always rewrite the worksheet, including when it is empty: leaving a stale
    # file in place would show conflicts that have since been settled.
    worksheet_path = out / "worksheet.csv"
    columns = list(worksheet[0]) if worksheet else WORKSHEET_COLUMNS
    with worksheet_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(worksheet)
    pending = sum(w["occurrences"] for w in worksheet)
    print(f"\nworksheet: {len(worksheet)} distinct undecided conflicts "
          f"({pending} rows) -> {worksheet_path}")
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    """Record a verdict for one row of the worksheet."""
    with Path(args.worksheet).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not 1 <= args.item <= len(rows):
        raise SystemExit(f"item {args.item} out of range (1-{len(rows)})")
    path = append_verdict(
        rows[args.item - 1], args.verdict, args.note, args.by, args.decisions
    )
    row = rows[args.item - 1]
    print(f"recorded {args.verdict}: {row['sheet']}.{row['column']} "
          f"({row['paper'][:44]}) -> {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="manifest-compare",
        description=(
            "Compare manifests extracted from the same manuscript by different "
            "annotators, reporting recall, precision and structural fidelity "
            "separately rather than as one agreement score."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    compare = sub.add_parser("compare", help="score a corpus from a pairing CSV")
    compare.add_argument(
        "pairs",
        help="CSV with columns human_file, gpt_file and optionally paper_title",
    )
    compare.add_argument(
        "--reference-dir",
        help="directory holding the reference manifests (default: <pairs dir>/human)",
    )
    compare.add_argument(
        "--test-dir",
        help="directory holding the test manifests (default: <pairs dir>/gpt)",
    )
    compare.add_argument("-o", "--out", default="out", help="output directory")
    compare.add_argument(
        "-v", "--verbose", action="store_true", help="print a scorecard per pair"
    )
    compare.set_defaults(func=cmd_compare)

    pair = sub.add_parser("pair", help="score a single pair of manifest files")
    pair.add_argument("reference", help="the reference (human) manifest")
    pair.add_argument("test", help="the test (model) manifest")
    pair.add_argument("--paper", default="", help="paper title for the report")
    pair.add_argument("-o", "--out", help="write artefacts to this directory")
    pair.set_defaults(func=cmd_pair)

    adj = sub.add_parser(
        "adjudicate",
        help="apply recorded rulings and verdicts to the conflicts, and build "
             "a worksheet of what is still undecided",
    )
    adj.add_argument("pairs", help="the same pairing CSV used by `compare`")
    adj.add_argument(
        "--decisions", default="adjudication",
        help="directory holding rulings.json and verdicts.csv",
    )
    adj.add_argument("--pdf-dir", help="directory of source PDFs, to add evidence")
    adj.add_argument("--cache", default=".cache/papers", help="extracted-text cache")
    adj.add_argument(
        "--test-grounded-only", action="store_true",
        help="worksheet only the conflicts where the test value is grounded in "
             "the paper and the reference value is not",
    )
    adj.add_argument("-o", "--out", default="out", help="output directory")
    adj.set_defaults(func=cmd_adjudicate)

    rec = sub.add_parser("record", help="record a verdict for one worksheet row")
    rec.add_argument("item", type=int, help="1-based row number in the worksheet")
    rec.add_argument(
        "verdict",
        choices=[v.value for v in Verdict if v is not Verdict.UNDECIDED],
        help="who was right",
    )
    rec.add_argument("--note", default="", help="rationale to record")
    rec.add_argument("--by", default="", help="who decided")
    rec.add_argument("--worksheet", default="out/worksheet.csv")
    rec.add_argument("--decisions", default="adjudication")
    rec.set_defaults(func=cmd_record)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
