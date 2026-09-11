"""Recording how conflicts were settled, so a run can reproduce the judgement.

Two kinds of decision are recorded, deliberately kept apart.

A **ruling** settles a whole class of conflict at once by naming the principle
that decides it -- for instance, that `input_molecule` means the molecule that
reaches the sequencer, which decides every `cDNA` vs `RNA` disagreement in the
corpus in the same direction. Rulings are matched by pattern, so they apply to
conflicts this corpus has not seen yet, and they carry their rationale with them.

A **verdict** settles one specific field in one specific paper, where no general
principle applies and someone simply had to read the manuscript.

Both live in files under `adjudication/` rather than in code, so the judgements
can be reviewed, cited and revised without touching the pipeline, and so a reader
of the published analysis can see exactly which calls a human made and why.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path

from .compare import FieldResult, Outcome, PairResult
from .normalise import fold

DEFAULT_DIR = Path("adjudication")
RULINGS_FILE = "rulings.json"
VERDICTS_FILE = "verdicts.csv"


class Verdict(str, Enum):
    """Who was right about a disagreement."""

    REFERENCE = "reference"
    """The reference (human) value is correct."""

    TEST = "test"
    """The test (model) value is correct."""

    BOTH = "both"
    """Both are acceptable readings of the paper."""

    NEITHER = "neither"
    """Neither is correct as the field is defined."""

    UNDECIDED = "undecided"
    """Not yet adjudicated."""


@dataclass
class Ruling:
    """A principle that settles a class of conflicts.

    `reference_pattern` and `test_pattern` are regular expressions matched
    against the *folded* values, so they are insensitive to case, Unicode
    punctuation and spacing -- the same normalisation the comparison uses.
    """

    id: str
    column: str
    verdict: str
    rationale: str
    reference_pattern: str = ".*"
    test_pattern: str = ".*"
    reference_max_words: int | None = None
    """Apply only when the reference value is at most this many words."""
    reference_min_words: int | None = None
    """Apply only when the reference value is at least this many words."""
    test_max_words: int | None = None
    """Apply only when the test value is at most this many words."""
    test_min_words: int | None = None
    """Apply only when the test value is at least this many words.

    Together these express an asymmetry of granularity -- a short label against a
    transcribed protocol -- without having to enumerate every phrasing. A ruling
    that matched on column alone would silently absorb genuine errors in the same
    field, so the shape of the disagreement has to be part of the condition.
    """
    columns: list[str] = field(default_factory=list)
    """Additional columns this ruling covers, beyond `column`."""
    decided_by: str = ""
    decided_on: str = ""
    note: str = ""

    def _applies_to(self, column: str) -> bool:
        return column == self.column or column in self.columns

    def matches(self, item: FieldResult) -> bool:
        if not self._applies_to(item.column):
            return False
        if re.search(self.reference_pattern, fold(item.reference)) is None:
            return False
        if re.search(self.test_pattern, fold(item.test)) is None:
            return False
        if self.reference_max_words is not None:
            if len(item.reference.split()) > self.reference_max_words:
                return False
        if self.test_min_words is not None:
            if len(item.test.split()) < self.test_min_words:
                return False
        if self.reference_min_words is not None:
            if len(item.reference.split()) < self.reference_min_words:
                return False
        if self.test_max_words is not None:
            if len(item.test.split()) > self.test_max_words:
                return False
        return True


@dataclass
class Verdicts:
    """The recorded judgements, both general and specific."""

    rulings: list[Ruling] = field(default_factory=list)
    items: dict[tuple[str, str, str, str, str], tuple[str, str]] = field(
        default_factory=dict
    )
    """(paper, sheet, column, reference, test) -> (verdict, note)."""

    @classmethod
    def load(cls, directory: str | Path = DEFAULT_DIR) -> "Verdicts":
        directory = Path(directory)
        rulings: list[Ruling] = []
        rulings_path = directory / RULINGS_FILE
        if rulings_path.exists():
            rulings = [
                Ruling(**r) for r in json.loads(rulings_path.read_text("utf-8"))
            ]
        items: dict = {}
        verdicts_path = directory / VERDICTS_FILE
        if verdicts_path.exists():
            with verdicts_path.open(newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    if not row.get("verdict"):
                        continue
                    items[
                        (
                            row["paper"],
                            row["sheet"],
                            row["column"],
                            row["reference_value"],
                            row["test_value"],
                        )
                    ] = (row["verdict"], row.get("note", ""))
        return cls(rulings, items)

    def decide(self, paper: str, item: FieldResult) -> tuple[Verdict, str, str]:
        """Settle one conflict, returning the verdict, its source and rationale.

        An item-level verdict wins over a ruling: someone looked at this exact
        field in this exact paper and decided it, which is stronger evidence than
        a general principle.
        """
        key = (paper, item.sheet, item.column, item.reference, item.test)
        if key in self.items:
            verdict, note = self.items[key]
            return Verdict(verdict), "verdict", note
        for ruling in self.rulings:
            if ruling.matches(item):
                return Verdict(ruling.verdict), f"ruling:{ruling.id}", ruling.rationale
        return Verdict.UNDECIDED, "", ""


VERDICT_COLUMNS = [
    "paper", "sheet", "column", "reference_value", "test_value",
    "verdict", "note", "decided_by", "decided_on",
]


def append_verdict(
    row: dict,
    verdict: str,
    note: str = "",
    decided_by: str = "",
    directory: str | Path = DEFAULT_DIR,
) -> Path:
    """Append one adjudicated item to `verdicts.csv`, keyed by its field values.

    Keying on the values rather than a row number means a verdict survives the
    worksheet being rebuilt, re-sorted or regenerated from a changed corpus --
    a judgement is about a disagreement, not about a position in a file.
    """
    import datetime

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / VERDICTS_FILE
    existing: list[dict] = []
    if path.exists():
        with path.open(newline="", encoding="utf-8") as handle:
            existing = list(csv.DictReader(handle))
    key = lambda r: (
        r["paper"], r["sheet"], r["column"], r["reference_value"], r["test_value"]
    )
    entry = {
        "paper": row["paper"],
        "sheet": row["sheet"],
        "column": row["column"],
        "reference_value": row["reference_value"],
        "test_value": row["test_value"],
        "verdict": verdict,
        "note": note,
        "decided_by": decided_by,
        "decided_on": datetime.date.today().isoformat(),
    }
    existing = [r for r in existing if key(r) != key(entry)] + [entry]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=VERDICT_COLUMNS)
        writer.writeheader()
        writer.writerows(existing)
    return path


def adjudicate(results: list[PairResult], verdicts: Verdicts) -> list[dict]:
    """Apply the recorded judgements to every conflict in a corpus."""
    decided: list[dict] = []
    for result in results:
        for item in result.fields:
            if item.outcome is not Outcome.CONFLICT:
                continue
            verdict, source, rationale = verdicts.decide(result.paper, item)
            decided.append(
                {
                    "paper": result.paper,
                    "sheet": item.sheet,
                    "column": item.column,
                    "field_class": item.field_class.value,
                    "reference_value": item.reference,
                    "test_value": item.test,
                    "verdict": verdict.value,
                    "decided_by": source,
                    "rationale": rationale,
                }
            )
    return decided


_WORD = re.compile(r"[a-z0-9]+")


def _evidence(paper, value: str, width: int = 260) -> str:
    """The passage of a paper where a value's distinctive terms cluster.

    Gives an adjudicator the sentence to judge against instead of making them
    search the PDF, which is the difference between a decision that takes ten
    seconds and one that takes ten minutes.
    """
    wanted = set(paper.distinctive(value))
    if not wanted:
        return ""
    hits = [
        (m.start(), m.group()) for m in _WORD.finditer(paper.text) if m.group() in wanted
    ]
    if not hits:
        return ""
    best_at, best_score = hits[0][0], 0
    for i, (start, _) in enumerate(hits):
        score = len({w for p, w in hits[i:] if p < start + width})
        if score > best_score:
            best_score, best_at = score, start
    return " ".join(paper.text[max(0, best_at - 60) : best_at + width].split())


def build_worksheet(
    results: list[PairResult],
    papers: dict[str, object],
    verdicts: "Verdicts | None" = None,
    only_test_grounded: bool = False,
    only_reference_grounded: bool = False,
) -> list[dict]:
    """Build a reviewable worksheet of conflicts still needing a human decision.

    Replicate rows repeat the same disagreement verbatim -- eight samples sharing
    one protocol produce eight identical conflicts -- so identical items are
    collapsed and carry an occurrence count. Deciding the same question eight
    times is not eight decisions.
    """
    from .grounding import Grounding

    grounded = {Grounding.VERBATIM, Grounding.GROUNDED}
    verdicts = verdicts or Verdicts()
    seen: dict[tuple, dict] = {}
    for result in results:
        paper = papers.get(result.paper)
        for item in result.fields:
            if item.outcome is not Outcome.CONFLICT:
                continue
            if verdicts.decide(result.paper, item)[0] is not Verdict.UNDECIDED:
                continue
            reference_grounding = test_grounding = None
            evidence = missing = ""
            if paper is not None:
                reference_grounding, _, missing_terms = paper.assess(item.reference)
                test_grounding, _, _ = paper.assess(item.test)
                missing = "; ".join(missing_terms[:5])
                evidence = _evidence(paper, item.test)
                if only_test_grounded and not (
                    test_grounding in grounded and reference_grounding not in grounded
                ):
                    continue
                # The mirror slice: the reference is traceable to the paper and
                # the test value is not. These are where the test manifest is
                # most likely to have invented something, so they are worked as
                # their own queue rather than mixed in with the rest.
                if only_reference_grounded and not (
                    reference_grounding in grounded and test_grounding not in grounded
                ):
                    continue
            key = (result.paper, item.sheet, item.column, item.reference, item.test)
            if key in seen:
                seen[key]["occurrences"] += 1
                continue
            seen[key] = {
                "paper": result.paper,
                "sheet": item.sheet,
                "column": item.column,
                "field_class": item.field_class.value,
                "reference_value": item.reference,
                "test_value": item.test,
                "reference_grounding": getattr(reference_grounding, "value", ""),
                "test_grounding": getattr(test_grounding, "value", ""),
                "reference_missing_terms": missing,
                "paper_evidence": evidence,
                "occurrences": 1,
                "verdict": "",
                "note": "",
            }
    return list(seen.values())


def adjudication_summary(decided: list[dict]) -> dict[str, int]:
    from collections import Counter

    return dict(Counter(d["verdict"] for d in decided))
