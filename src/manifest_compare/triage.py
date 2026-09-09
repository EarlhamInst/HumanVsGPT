"""Sorting the conflict queue by what it would actually take to settle each item.

A `conflict` verdict means only that two values disagreed, and inspection shows
that bucket is over-broad. It holds at least four different situations, needing
four different kinds of work:

* an accession or taxon ID that differs -- settled against a public archive, no
  paper required;
* a vocabulary clash repeated across many papers -- one terminology decision,
  not N independent errors;
* a quantity recorded as a range by one annotator and a point by the other --
  usually a precision difference rather than a contradiction;
* a genuine factual disagreement -- the only kind that needs the manuscript.

Triaging first means the expensive step (reading papers) runs only on the items
that need it, and stops a systematic terminology difference from being counted as
hundreds of separate mistakes.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from enum import Enum

from .compare import FieldResult, Outcome, PairResult
from .normalise import accessions, canonical, fold, quantity
from .schema import FieldClass

#: A (column, value-pair) disagreement seen in at least this many papers is
#: treated as a terminology difference rather than as repeated error.
SYSTEMATIC_MIN_PAPERS = 3

_RANGE = re.compile(r"(-?\d+(?:\.\d+)?)\s*(?:-|--|to|~)\s*(-?\d+(?:\.\d+)?)")


class Route(str, Enum):
    """How a conflict should be resolved."""

    ARCHIVE = "archive_checkable"
    """Both values are accessions or database IDs; resolvable online."""

    VOCABULARY = "vocabulary_variant"
    """The same disagreement recurs across papers; a terminology decision."""

    PRECISION = "precision_variant"
    """Numeric values consistent with one another (a range and a point in it)."""

    MANUSCRIPT = "needs_manuscript"
    """A genuine disagreement only the paper can settle."""


@dataclass(frozen=True)
class TriagedConflict:
    paper: str
    sheet: str
    column: str
    field_class: FieldClass
    reference: str
    test: str
    route: Route
    note: str = ""


def _numbers(value: str) -> tuple[float, float] | None:
    """The interval a value denotes: a range, or a point as a degenerate range."""
    match = _RANGE.search(fold(value))
    if match:
        low, high = float(match.group(1)), float(match.group(2))
        return (min(low, high), max(low, high))
    parsed = quantity(value)
    return (parsed[0], parsed[0]) if parsed else None


def _consistent(reference: str, test: str) -> bool:
    """True when two quantities overlap -- a point inside a range, say."""
    a, b = _numbers(reference), _numbers(test)
    if a is None or b is None:
        return False
    return a[0] <= b[1] and b[0] <= a[1]


def triage(results: list[PairResult]) -> list[TriagedConflict]:
    """Route every conflict in the corpus to the cheapest way of settling it."""
    conflicts: list[tuple[str, FieldResult]] = [
        (r.paper, f)
        for r in results
        for f in r.fields
        if f.outcome is Outcome.CONFLICT
    ]

    # A disagreement counts as systematic on the number of distinct papers it
    # appears in, not the number of rows: eight replicate rows in one manifest
    # are one decision, not eight.
    #
    # Grouping is by column, not by the exact pair of values. The two annotators
    # phrase the same terminology clash differently in each paper -- `cDNA` meets
    # `Polyadenylated messenger RNA` in one and `mRNA` in the next -- so matching
    # on value pairs splits a single convention problem into a dozen singletons.
    # What identifies it is that the *field* disagrees wherever it is recorded.
    papers_per_column: dict[str, set[str]] = {}
    for paper, item in conflicts:
        papers_per_column.setdefault(item.column, set()).add(paper)

    #: A column is a terminology problem only if it is a closed vocabulary; free
    #: prose disagreeing across papers is just prose disagreeing.
    vocabulary_columns = {
        column
        for column, papers in papers_per_column.items()
        if len(papers) >= SYSTEMATIC_MIN_PAPERS
        and any(
            item.field_class in (FieldClass.VOCAB, FieldClass.NUMERIC)
            for _, item in conflicts
            if item.column == column
        )
    }

    triaged: list[TriagedConflict] = []
    for paper, item in conflicts:
        note = ""
        if item.field_class is FieldClass.IDENTIFIER and (
            accessions(item.reference) or accessions(item.test)
        ):
            route = Route.ARCHIVE
            note = "resolve against the source archive"
        elif (
            item.column in vocabulary_columns
            and item.field_class is FieldClass.VOCAB
        ):
            route = Route.VOCABULARY
            note = f"column disagrees in {len(papers_per_column[item.column])} papers"
        elif item.field_class is FieldClass.NUMERIC and _consistent(
            item.reference, item.test
        ):
            route = Route.PRECISION
            note = "values overlap; likely range vs point"
        else:
            route = Route.MANUSCRIPT
        triaged.append(
            TriagedConflict(
                paper, item.sheet, item.column, item.field_class,
                item.reference, item.test, route, note,
            )
        )
    return triaged


def triage_summary(triaged: list[TriagedConflict]) -> dict[str, int]:
    return dict(Counter(t.route.value for t in triaged))
