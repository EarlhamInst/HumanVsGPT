"""Scoring an aligned pair of manifests.

The comparison deliberately does not produce a single agreement percentage.
Three things that a single number would conflate are kept apart:

* **Recall** -- of what the reference recorded, how much did the test manifest
  also capture? This is the question "did it miss anything".
* **Precision** -- of what the test manifest asserted where the reference also
  spoke, how much held up? This is the question "did it make things up".
The `file` sheet is excluded before any of this (see `schema.EXCLUDED_SHEETS`):
neither annotator recorded real raw-file entries, so comparing them would score a
convention neither was following.

* **Structure** -- are there the right number of rows? A manifest can agree on
  every cell and still misrepresent the study if it has collapsed eight
  sequencing runs into one row.

Referential integrity is deliberately *not* checked or reported. Neither manifest
has been validated against the schema, and a dangling foreign key says something
about a spreadsheet's internal consistency, not about how faithfully a study was
read out of a paper. Surrogate and foreign keys are arbitrary strings on both
sides -- `cao_2023_s1` and `SAMPLE_QI319_FV_REP1` name the same sample -- so they
are never scored. They are used only inside `align`, to work out which row
corresponds to which.

* **Coverage** -- how much of the manifest each annotator filled in at all,
  reported separately for the two sides and never as a score. It is a
  *description* of effort, not a measure of quality: a manifest can be filled
  from end to end with plausible invention, and one left half blank may be
  scrupulous about only recording what the paper states. Because the reference
  is unvalidated, nothing here can tell those apart, so coverage is reported
  and left unjudged.

Fields the test manifest filled and the reference left blank are counted in none
of the scored metrics. A blank reference cell means *unknown*, not *false*, so
such fields are routed to an adjudication queue instead of being scored either
way.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum

from .align import Alignment, SheetAlignment, align
from .io import Manifest
from .normalise import accessions, canonical, fold, quantity, tokens
from .schema import (
    CLASS_WEIGHTS,
    PRIMARY_KEY,
    SCORED_SHEETS,
    SHEET_WEIGHTS,
    FieldClass,
    classify,
)

#: Relative tolerance for numeric agreement. Tight enough that the 26 degC /
#: 27 degC disagreement in the Cao pair registers as a genuine conflict.
NUMERIC_RTOL = 0.005

#: Token overlap above which two free-text values are treated as equivalent.
TEXT_EQUIVALENT = 0.75

#: Token overlap below which two free-text values are treated as divergent.
TEXT_DIVERGENT = 0.25

#: Character-level similarity above which a difference is read as a typo.
TEXT_NEAR_IDENTICAL = 0.92


class Outcome(str, Enum):
    """How one field compared between the two manifests."""

    EXACT = "exact"
    EQUIVALENT = "equivalent"
    TEST_MORE_SPECIFIC = "test_more_specific"
    TEST_LESS_SPECIFIC = "test_less_specific"
    CONFLICT = "conflict"
    MISSING_IN_TEST = "missing_in_test"
    TEST_ONLY = "test_only"
    BOTH_ABSENT = "both_absent"


#: Outcomes that count as the test manifest having captured the reference fact.
CAPTURED: frozenset[Outcome] = frozenset(
    {Outcome.EXACT, Outcome.EQUIVALENT, Outcome.TEST_MORE_SPECIFIC}
)

#: Outcomes where both manifests spoke and can be scored against each other.
COMPARABLE: frozenset[Outcome] = CAPTURED | {
    Outcome.TEST_LESS_SPECIFIC,
    Outcome.CONFLICT,
}

#: Outcomes a human or model must resolve against the source paper.
NEEDS_ADJUDICATION: frozenset[Outcome] = frozenset(
    {Outcome.CONFLICT, Outcome.TEST_ONLY}
)


@dataclass(frozen=True)
class FieldResult:
    """The comparison of one column within one aligned row pair."""

    sheet: str
    column: str
    field_class: FieldClass
    outcome: Outcome
    reference: str
    test: str
    detail: str = ""

    @property
    def weight(self) -> float:
        return CLASS_WEIGHTS[self.field_class] * SHEET_WEIGHTS.get(self.sheet, 1.0)


@dataclass
class StructureResult:
    """Structural findings for one sheet."""

    sheet: str
    reference_rows: int
    test_rows: int
    reference_distinct: int
    test_distinct: int
    matched: int
    ambiguous: int
    missing_in_test: bool = False
    """The sheet is absent from the test workbook entirely."""

    @property
    def cardinality_ok(self) -> bool:
        return self.reference_rows == self.test_rows

    @property
    def coverage(self) -> float:
        return self.matched / self.reference_rows if self.reference_rows else 1.0


@dataclass
class PairResult:
    """Everything learned about one reference/test manifest pair."""

    paper: str
    reference_label: str
    test_label: str
    reference_provenance: dict
    test_provenance: dict
    fields: list[FieldResult] = field(default_factory=list)
    structure: list[StructureResult] = field(default_factory=list)
    reference_filled: int = 0
    """Non-empty, non-surrogate cells in the reference manifest."""
    test_filled: int = 0
    """The same for the test manifest."""
    reference_cells: int = 0
    """Cells available to fill in the reference: rows x comparable columns."""
    test_cells: int = 0

    # --- headline metrics ---------------------------------------------------

    def _counts(self) -> dict[Outcome, int]:
        counts = {o: 0 for o in Outcome}
        for result in self.fields:
            counts[result.outcome] += 1
        return counts

    @property
    def counts(self) -> dict[str, int]:
        return {o.value: n for o, n in self._counts().items()}

    def _weighted(self, outcomes: frozenset[Outcome]) -> float:
        return sum(f.weight for f in self.fields if f.outcome in outcomes)

    @property
    def recall(self) -> float:
        """Of fields the reference populated, the share the test also captured."""
        denominator = self._weighted(CAPTURED | {Outcome.TEST_LESS_SPECIFIC,
                                                 Outcome.CONFLICT,
                                                 Outcome.MISSING_IN_TEST})
        return self._weighted(CAPTURED) / denominator if denominator else 0.0

    @property
    def precision(self) -> float:
        """Of fields both populated, the share where the test held up."""
        denominator = self._weighted(COMPARABLE)
        return self._weighted(CAPTURED) / denominator if denominator else 0.0

    @property
    def structural_fidelity(self) -> float:
        """Share of sheets with matching row counts and no missing sheet."""
        scored = [s for s in self.structure if s.reference_rows or s.test_rows]
        if not scored:
            return 0.0
        good = sum(1 for s in scored if s.cardinality_ok and not s.missing_in_test)
        return good / len(scored)

    @property
    def reference_fill_rate(self) -> float:
        return self.reference_filled / self.reference_cells if self.reference_cells else 0.0

    @property
    def test_fill_rate(self) -> float:
        return self.test_filled / self.test_cells if self.test_cells else 0.0

    @property
    def coverage_ratio(self) -> float:
        """Test fields filled per reference field filled.

        Above 1.0 the test manifest asserted more than the reference did. That is
        not by itself better or worse -- see the note on coverage above. It is
        reported so the recall and precision figures are read in the light of how
        much each side attempted.
        """
        return self.test_filled / self.reference_filled if self.reference_filled else 0.0

    @property
    def adjudication_queue(self) -> list[FieldResult]:
        """Fields that cannot be scored without consulting the source paper."""
        return [f for f in self.fields if f.outcome in NEEDS_ADJUDICATION]


# --- Field comparison --------------------------------------------------------

def _specificity(reference: str, test: str) -> Outcome | None:
    """Outcome implied by one value's tokens containing the other's, if any."""
    ref_tokens, test_tokens = tokens(reference), tokens(test)
    if not ref_tokens or not test_tokens:
        return None
    if ref_tokens == test_tokens:
        return Outcome.EQUIVALENT
    if ref_tokens < test_tokens:
        return Outcome.TEST_MORE_SPECIFIC
    if test_tokens < ref_tokens:
        return Outcome.TEST_LESS_SPECIFIC
    return None


def compare_identifier(reference: str, test: str) -> tuple[Outcome, str]:
    """Compare by the accessions each value contains, not by the whole string.

    The two manifests routinely bury the same accession in differently-worded
    prose, and put it in different columns. Extracting and set-comparing is
    robust to both; comparing the containing cell is not.
    """
    ref_hits = {a for hits in accessions(reference).values() for a in hits}
    test_hits = {a for hits in accessions(test).values() for a in hits}
    if ref_hits or test_hits:
        if ref_hits == test_hits:
            return Outcome.EXACT, f"{len(ref_hits)} accession(s) agree"
        if ref_hits < test_hits:
            return Outcome.TEST_MORE_SPECIFIC, f"test adds {sorted(test_hits - ref_hits)}"
        if test_hits < ref_hits:
            return Outcome.TEST_LESS_SPECIFIC, f"test omits {sorted(ref_hits - test_hits)}"
        if ref_hits & test_hits:
            return Outcome.CONFLICT, f"partial overlap; test-only {sorted(test_hits - ref_hits)}"
        return Outcome.CONFLICT, f"disjoint: {sorted(ref_hits)} vs {sorted(test_hits)}"
    if fold(reference) == fold(test):
        return Outcome.EXACT, ""
    return Outcome.CONFLICT, "no accession recognised in either value"


def compare_numeric(reference: str, test: str) -> tuple[Outcome, str]:
    """Compare magnitudes with tolerance, treating an absent unit as compatible."""
    ref_q, test_q = quantity(reference), quantity(test)
    if ref_q is None or test_q is None:
        return (
            (Outcome.EXACT, "") if fold(reference) == fold(test)
            else (Outcome.CONFLICT, "not parseable as a quantity")
        )
    ref_value, ref_unit = ref_q
    test_value, test_unit = test_q
    if ref_unit and test_unit and ref_unit != test_unit:
        return Outcome.CONFLICT, f"unit mismatch: {ref_unit} vs {test_unit}"
    scale = max(abs(ref_value), abs(test_value), 1e-9)
    if abs(ref_value - test_value) / scale <= NUMERIC_RTOL:
        return (
            (Outcome.EXACT, "") if fold(reference) == fold(test)
            else (Outcome.EQUIVALENT, "same quantity, different formatting")
        )
    return Outcome.CONFLICT, f"{ref_value} vs {test_value}"


def compare_vocab(column: str, reference: str, test: str) -> tuple[Outcome, str]:
    """Compare after mapping both values onto their canonical term."""
    ref_canonical, test_canonical = canonical(column, reference), canonical(column, test)
    if ref_canonical == test_canonical:
        return (
            (Outcome.EXACT, "") if reference == test
            else (Outcome.EQUIVALENT, f"both -> '{ref_canonical}'")
        )
    implied = _specificity(reference, test)
    if implied:
        return implied, "by token containment"
    ratio = SequenceMatcher(None, ref_canonical, test_canonical).ratio()
    if ratio >= TEXT_NEAR_IDENTICAL:
        return Outcome.EQUIVALENT, f"near-identical ({ratio:.2f}); likely a typo"
    return Outcome.CONFLICT, f"'{ref_canonical}' vs '{test_canonical}'"


def compare_text(reference: str, test: str) -> tuple[Outcome, str]:
    """Compare free prose by token overlap, never by string equality.

    Prose is the least objectively checkable class, so the verdicts here are
    deliberately coarse and weighted lightly. A divergent verdict is a referral
    for adjudication, not a finding of error.
    """
    if fold(reference) == fold(test):
        return Outcome.EXACT, ""

    # Near-identical strings are a spelling difference, not a disagreement. The
    # human Cao manifest records the instrument as 'llumina NovaSeq 6000' -- a
    # dropped capital I. Reporting that as a conflict would be a finding about
    # the reference's typing, not about the test manifest.
    ratio = SequenceMatcher(None, fold(reference), fold(test)).ratio()
    if ratio >= TEXT_NEAR_IDENTICAL:
        return Outcome.EQUIVALENT, f"near-identical strings ({ratio:.2f}); likely a typo"

    # Strict token containment is conclusive on its own: every word of the
    # shorter value appears in the longer. 'Root' inside 'Primary root tip
    # containing root cap...' is elaboration, however low the overlap ratio.
    implied = _specificity(reference, test)
    if implied is Outcome.EQUIVALENT:
        return Outcome.EQUIVALENT, "same tokens"
    ref_tokens, test_tokens = tokens(reference), tokens(test)
    union = ref_tokens | test_tokens
    overlap = len(ref_tokens & test_tokens) / len(union) if union else 0.0
    if implied:
        return implied, f"token containment, overlap {overlap:.2f}"
    if overlap >= TEXT_EQUIVALENT:
        return Outcome.EQUIVALENT, f"overlap {overlap:.2f}"
    if overlap >= TEXT_DIVERGENT:
        return (
            Outcome.TEST_MORE_SPECIFIC if len(test_tokens) > len(ref_tokens)
            else Outcome.TEST_LESS_SPECIFIC
        ), f"partial overlap {overlap:.2f}"
    return Outcome.CONFLICT, f"low overlap {overlap:.2f}"


def compare_field(
    sheet: str, column: str, reference: str, test: str
) -> FieldResult:
    """Compare one column of one aligned row pair."""
    field_class = classify(column)
    reference, test = (reference or "").strip(), (test or "").strip()

    if not reference and not test:
        outcome, detail = Outcome.BOTH_ABSENT, ""
    elif reference and not test:
        outcome, detail = Outcome.MISSING_IN_TEST, ""
    elif test and not reference:
        outcome, detail = Outcome.TEST_ONLY, "reference silent; verify against source"
    elif field_class is FieldClass.IDENTIFIER:
        outcome, detail = compare_identifier(reference, test)
    elif field_class is FieldClass.NUMERIC:
        outcome, detail = compare_numeric(reference, test)
    elif field_class is FieldClass.VOCAB:
        outcome, detail = compare_vocab(column, reference, test)
    else:
        outcome, detail = compare_text(reference, test)

    return FieldResult(
        sheet=sheet,
        column=column,
        field_class=field_class,
        outcome=outcome,
        reference=reference,
        test=test,
        detail=detail,
    )


# --- Structural checks -------------------------------------------------------

def _structure(name: str, alignment: SheetAlignment, absent: bool) -> StructureResult:
    return StructureResult(
        sheet=name,
        reference_rows=alignment.ref_rows,
        test_rows=alignment.test_rows,
        reference_distinct=alignment.distinct_ref,
        test_distinct=alignment.distinct_test,
        matched=len(alignment.pairs),
        ambiguous=alignment.ambiguous_pairs,
        missing_in_test=absent,
    )


def _coverage(manifest: Manifest) -> tuple[int, int]:
    """Count filled and available cells across the compared sheets.

    Availability is rows x comparable columns: the cells the annotator could
    have filled given the rows they chose to record. Surrogate keys are excluded
    because they are bookkeeping, not extracted content.
    """
    filled = available = 0
    for name in SCORED_SHEETS:
        sheet = manifest.get(name)
        if not sheet:
            continue
        columns = [
            c for c in sheet.columns if classify(c) is not FieldClass.SURROGATE
        ]
        available += len(columns) * len(sheet.rows)
        filled += sum(1 for row in sheet.rows for c in columns if row.get(c))
    return filled, available


def compare_manifests(
    reference: Manifest,
    test: Manifest,
    paper: str = "",
    alignment: Alignment | None = None,
) -> PairResult:
    """Align two manifests if needed, then score every aligned field."""
    alignment = alignment or align(reference, test)
    result = PairResult(
        paper=paper or reference.study_title,
        reference_label=reference.label,
        test_label=test.label,
        reference_provenance=reference.provenance.as_dict(),
        test_provenance=test.provenance.as_dict(),
    )

    result.reference_filled, result.reference_cells = _coverage(reference)
    result.test_filled, result.test_cells = _coverage(test)

    for name in SCORED_SHEETS:
        sheet_alignment = alignment.sheets[name]
        ref_sheet, test_sheet = reference.get(name), test.get(name)
        result.structure.append(
            _structure(name, sheet_alignment, absent=test_sheet is None)
        )
        if not ref_sheet or not test_sheet:
            # An absent sheet is a structural finding; its fields are recorded as
            # missing so recall reflects the loss rather than ignoring it.
            if ref_sheet and not test_sheet:
                for row in ref_sheet.rows:
                    for column, value in row.items():
                        if classify(column) is FieldClass.SURROGATE or not value:
                            continue
                        result.fields.append(
                            FieldResult(name, column, classify(column),
                                        Outcome.MISSING_IN_TEST, value, "",
                                        "sheet absent from test manifest")
                        )
            continue

        columns = [
            c for c in dict.fromkeys(ref_sheet.columns + test_sheet.columns)
            if classify(c) is not FieldClass.SURROGATE
        ]
        for pair in sheet_alignment.pairs:
            ref_row = ref_sheet.rows[pair.ref_index]
            test_row = test_sheet.rows[pair.test_index]
            for column in columns:
                outcome = compare_field(
                    name, column, ref_row.get(column, ""), test_row.get(column, "")
                )
                if outcome.outcome is not Outcome.BOTH_ABSENT:
                    result.fields.append(outcome)

        # Reference rows with no partner are a wholesale loss, not a field diff.
        for index in sheet_alignment.unmatched_ref:
            for column, value in ref_sheet.rows[index].items():
                if classify(column) is FieldClass.SURROGATE or not value:
                    continue
                result.fields.append(
                    FieldResult(name, column, classify(column),
                                Outcome.MISSING_IN_TEST, value, "",
                                "row unmatched in test manifest")
                )

    return result
