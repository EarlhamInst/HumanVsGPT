"""Matching rows across two manifests that describe the same study.

Two manifests of one paper agree on the biology and disagree on everything
presentational. In the Cao pair the human lists samples B104, B104, Qi319,
Qi319, B104, B104, Qi319, Qi319 while GPT lists Qi319 x4 then B104 x4; the human
calls a sample `cao_2023_s1` and GPT calls the same sample
`SAMPLE_QI319_FV_REP1`. Comparing by row position, or by identifier, would
report near-total disagreement between two files that largely agree.

So rows are matched on *content* before any field is scored, and the match is
propagated along the entity graph: once samples are paired, a cell suspension
that descends from paired samples inherits evidence for its own pairing. That
turns eight independent matching problems into one connected one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations, permutations

from .io import Manifest, Sheet
from .normalise import accessions, canonical, fold, tokens
from .schema import (
    LINKS,
    EXCLUDED_SHEETS,
    PRIMARY_KEY,
    SCORED_SHEETS,
    SINGLETON_SHEETS,
    FieldClass,
    classify,
)

#: Row pairs scoring below this are left unmatched rather than forced together.
MATCH_THRESHOLD = 0.10

#: Weight of evidence that a row's parents are already paired.
LINK_BONUS = 0.45

#: Weight of a shared external accession -- near-conclusive evidence of identity.
ACCESSION_BONUS = 1.0

#: A match whose runner-up scores within this margin is reported as ambiguous.
AMBIGUITY_MARGIN = 0.05


@dataclass(frozen=True)
class RowPair:
    """One matched pair of rows, with the evidence that matched them."""

    ref_index: int
    test_index: int
    score: float
    via: str
    ambiguous: bool = False
    """True when a rival row scored within `AMBIGUITY_MARGIN` of this match, so
    the pairing is under-determined by the evidence in the two manifests."""


@dataclass
class SheetAlignment:
    """The row correspondence for one sheet."""

    sheet: str
    pairs: list[RowPair] = field(default_factory=list)
    unmatched_ref: list[int] = field(default_factory=list)
    unmatched_test: list[int] = field(default_factory=list)
    ref_rows: int = 0
    test_rows: int = 0
    distinct_ref: int = 0
    distinct_test: int = 0
    """Rows remaining once rows identical in every non-surrogate field are
    collapsed. A sheet with many rows but one distinct signature is a
    fill-down artifact, not that many entities."""

    @property
    def cardinality_matches(self) -> bool:
        return self.ref_rows == self.test_rows

    @property
    def ref_degenerate(self) -> int:
        """Reference rows that duplicate another row's entire content."""
        return self.ref_rows - self.distinct_ref

    @property
    def test_degenerate(self) -> int:
        return self.test_rows - self.distinct_test

    @property
    def ambiguous_pairs(self) -> int:
        return sum(1 for p in self.pairs if p.ambiguous)

    @property
    def coverage(self) -> float:
        """Fraction of reference rows that found a partner."""
        return len(self.pairs) / self.ref_rows if self.ref_rows else 1.0


@dataclass
class Alignment:
    """Row correspondences for every sheet, plus the surrogate-ID mapping."""

    sheets: dict[str, SheetAlignment] = field(default_factory=dict)
    id_map: dict[str, dict[str, str]] = field(default_factory=dict)
    """Per sheet: reference surrogate ID -> test surrogate ID."""

    def __getitem__(self, sheet: str) -> SheetAlignment:
        return self.sheets[sheet]


# --- Optimal assignment ------------------------------------------------------

def _hungarian(cost: list[list[float]]) -> list[int]:
    """Minimum-cost assignment for a rectangular matrix (Jonker-Volgenant).

    Returns, for each row, the column assigned to it, or -1. Greedy matching was
    the obvious alternative but can be defeated by near-ties between replicate
    rows -- exactly what these manifests are full of, since replicates differ in
    almost no field. An optimal assignment removes that failure mode and makes
    the result independent of row order.

    Contract: costs must be non-positive, as they are here (cost = -similarity).
    The matrix is squared off with zero-cost padding, so a row can only go
    unassigned when there are more rows than columns; with non-positive costs
    that is harmless, because taking any real column is never worse than taking
    none. Callers discard weak pairings afterwards via `MATCH_THRESHOLD`.
    Verified optimal against exhaustive search over this regime in the tests.
    """
    n_rows = len(cost)
    if n_rows == 0:
        return []
    n_cols = len(cost[0])
    if n_cols == 0:
        return [-1] * n_rows
    size = max(n_rows, n_cols)
    big = 1e9
    # Pad to square; padding entries carry zero cost and are discarded after.
    matrix = [
        [cost[r][c] if r < n_rows and c < n_cols else 0.0 for c in range(size)]
        for r in range(size)
    ]
    u = [0.0] * (size + 1)
    v = [0.0] * (size + 1)
    p = [0] * (size + 1)
    way = [0] * (size + 1)
    for i in range(1, size + 1):
        p[0] = i
        j0 = 0
        minv = [big] * (size + 1)
        used = [False] * (size + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], big, 0
            for j in range(1, size + 1):
                if used[j]:
                    continue
                cur = matrix[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j], way[j] = cur, j0
                if minv[j] < delta:
                    delta, j1 = minv[j], j
            for j in range(size + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0], j0 = p[j1], j1
    assignment = [-1] * n_rows
    for j in range(1, size + 1):
        row, col = p[j] - 1, j - 1
        if row < n_rows and col < n_cols:
            assignment[row] = col
    return assignment


def _assign(cost: list[list[float]]) -> list[int]:
    """Optimal assignment, using SciPy when installed and falling back otherwise.

    The pure-Python Hungarian above is the reference implementation and keeps the
    package usable with no scientific stack, but it is O(n^3): one manifest in
    this corpus carries 2182 sample rows, which is minutes of Python and
    milliseconds of SciPy. Both are exercised against each other in the tests, so
    results do not depend on which path runs.
    """
    if not cost or not cost[0]:
        return [-1] * len(cost)
    try:
        import numpy as np
        from scipy.optimize import linear_sum_assignment
    except ImportError:
        return _hungarian(cost)
    rows, cols = linear_sum_assignment(np.asarray(cost, dtype=float))
    assignment = [-1] * len(cost)
    for r, c in zip(rows.tolist(), cols.tolist()):
        assignment[r] = c
    return assignment


def _brute_force(cost: list[list[float]]) -> float:
    """Optimal cost by exhaustive search; for testing `_hungarian` only.

    Mirrors the padded semantics of `_hungarian`: any row may be left
    unassigned at zero cost, and any subset of rows may take columns.
    """
    n, m = len(cost), len(cost[0])
    best = 0.0  # assign nothing
    for size in range(1, min(n, m) + 1):
        for rows in combinations(range(n), size):
            for cols in permutations(range(m), size):
                total = sum(cost[r][c] for r, c in zip(rows, cols))
                best = min(best, total)
    return best


# --- Row similarity ----------------------------------------------------------

def _comparable_columns(ref: Sheet, test: Sheet) -> list[str]:
    """Columns usable as matching evidence: populated somewhere, not surrogate."""
    names = set(ref.populated_columns()) | set(test.populated_columns())
    return sorted(c for c in names if classify(c) is not FieldClass.SURROGATE)


def _row_accessions(row: dict[str, str]) -> frozenset[str]:
    found: set[str] = set()
    for column, value in row.items():
        if classify(column) is FieldClass.SURROGATE:
            continue
        for hits in accessions(value).values():
            found |= hits
    return frozenset(found)


def _content_tokens(row: dict[str, str], columns: list[str]) -> frozenset[str]:
    bag: set[str] = set()
    for column in columns:
        value = row.get(column)
        if value:
            bag |= tokens(canonical(column, value))
    return frozenset(bag)


@dataclass(frozen=True)
class _RowFeatures:
    """Per-row matching features, computed once rather than per candidate pair.

    Row similarity is an O(rows x rows) comparison and some sheets carry several
    hundred rows, so tokenising inside the loop made whole-corpus runs
    impractical. Extracting features up front makes each comparison two set
    operations.
    """

    tokens: frozenset[str]
    accessions: frozenset[str]


#: Foreign-key columns per sheet: a row's parents are part of its identity.
_FOREIGN_KEYS: dict[str, frozenset[str]] = {}
for _link in LINKS:
    if _link.to_sheet != "study":
        _FOREIGN_KEYS.setdefault(_link.from_sheet, set()).add(_link.column)
_FOREIGN_KEYS = {k: frozenset(v) for k, v in _FOREIGN_KEYS.items()}


def content_signature(sheet: str, row: dict[str, str], columns: list[str]) -> tuple:
    """A row's identity: its described content plus which parents it hangs from.

    A row's own primary key is arbitrary and excluded -- `cao_2023_s1` and
    `SAMPLE_QI319_FV_REP1` name the same thing. Its *foreign* keys are not
    arbitrary: eight cell suspensions that carry identical protocol text are
    still eight distinct suspensions when they point at eight distinct samples.
    Ignoring that would condemn every properly-replicated manifest as degenerate.

    What remains genuinely degenerate is a row indistinguishable from another in
    both content and parentage. One human manifest carries 2182 `sample` rows --
    a root entity, so parented only by the study -- identical in every field but
    an auto-incremented `sample_id`. That is a spreadsheet fill-down, and without
    this test it would read as 2182 real samples the other manifest missed.
    """
    foreign = _FOREIGN_KEYS.get(sheet, frozenset())
    parts = []
    for column in columns:
        value = row.get(column)
        if not value:
            continue
        if column in foreign:
            parts.append((column, value))
        elif classify(column) is not FieldClass.SURROGATE:
            parts.append((column, canonical(column, value)))
    return tuple(sorted(parts))


def _distinct(sheet: str, rows: list[dict[str, str]], columns: list[str]) -> int:
    return len({content_signature(sheet, r, columns) for r in rows})


def _features(rows: list[dict[str, str]], columns: list[str]) -> list[_RowFeatures]:
    return [
        _RowFeatures(_content_tokens(row, columns), _row_accessions(row))
        for row in rows
    ]


def _similarity(
    ref: _RowFeatures,
    test: _RowFeatures,
    link_evidence: float,
) -> tuple[float, str]:
    """Similarity of two rows in [0, 1+], with the dominant evidence named."""
    if ref.accessions & test.accessions:
        return 1.0 + ACCESSION_BONUS, "accession"

    union = ref.tokens | test.tokens
    jaccard = len(ref.tokens & test.tokens) / len(union) if union else 0.0
    score = jaccard + link_evidence
    via = "link" if link_evidence and link_evidence > jaccard else "content"
    return score, via


def _link_evidence(
    sheet: str,
    ref_row: dict[str, str],
    test_row: dict[str, str],
    id_map: dict[str, dict[str, str]],
) -> float:
    """Evidence from parents already paired in an earlier sheet."""
    evidence = 0.0
    for link in LINKS:
        if link.from_sheet != sheet or link.to_sheet == "study":
            continue
        mapping = id_map.get(link.to_sheet)
        if not mapping:
            continue
        ref_parent = ref_row.get(link.column, "")
        test_parent = test_row.get(link.column, "")
        if ref_parent and test_parent and mapping.get(ref_parent) == test_parent:
            evidence += LINK_BONUS
    return evidence


def align_sheet(
    name: str,
    ref: Sheet | None,
    test: Sheet | None,
    id_map: dict[str, dict[str, str]],
) -> SheetAlignment:
    """Match the rows of one sheet across two manifests."""
    ref_rows = ref.rows if ref else []
    test_rows = test.rows if test else []
    result = SheetAlignment(sheet=name, ref_rows=len(ref_rows), test_rows=len(test_rows))
    if not ref_rows or not test_rows:
        cols = sorted({c for r in ref_rows + test_rows for c in r})
        result.distinct_ref = _distinct(name, ref_rows, cols)
        result.distinct_test = _distinct(name, test_rows, cols)
        result.unmatched_ref = list(range(len(ref_rows)))
        result.unmatched_test = list(range(len(test_rows)))
        return result

    if name in SINGLETON_SHEETS and len(ref_rows) == 1 and len(test_rows) == 1:
        # A sheet that holds one row per study has only one possible
        # correspondence. Scoring it by content would let a verbose GPT protocol
        # description fall below threshold against a terse human one and leave
        # the study unmatched against itself.
        result.distinct_ref = result.distinct_test = 1
        result.pairs.append(RowPair(0, 0, 1.0, "singleton"))
        return result

    columns = _comparable_columns(ref, test) if ref and test else []
    all_columns = sorted({c for r in ref_rows + test_rows for c in r})
    result.distinct_ref = _distinct(name, ref_rows, all_columns)
    result.distinct_test = _distinct(name, test_rows, all_columns)
    ref_features = _features(ref_rows, columns)
    test_features = _features(test_rows, columns)
    scores = [
        [
            _similarity(
                ref_features[i],
                test_features[j],
                _link_evidence(name, ref_row, test_row, id_map),
            )
            for j, test_row in enumerate(test_rows)
        ]
        for i, ref_row in enumerate(ref_rows)
    ]
    cost = [[-s for s, _ in row] for row in scores]
    assignment = _assign(cost)

    matched_test: set[int] = set()
    for ref_index, test_index in enumerate(assignment):
        if test_index < 0:
            continue
        score, via = scores[ref_index][test_index]
        if score < MATCH_THRESHOLD:
            continue
        rivals = sorted(
            (s for j, (s, _) in enumerate(scores[ref_index]) if j != test_index),
            reverse=True,
        )
        ambiguous = bool(rivals) and (score - rivals[0]) <= AMBIGUITY_MARGIN
        result.pairs.append(
            RowPair(ref_index, test_index, round(score, 4), via, ambiguous)
        )
        matched_test.add(test_index)
    matched_ref = {p.ref_index for p in result.pairs}
    result.unmatched_ref = [i for i in range(len(ref_rows)) if i not in matched_ref]
    result.unmatched_test = [i for i in range(len(test_rows)) if i not in matched_test]
    return result


#: Sheets are aligned parents-first so that link evidence is available
#: downstream. Excluded sheets are not aligned at all.
ALIGN_ORDER: tuple[str, ...] = tuple(
    s
    for s in (
        "study",
        "dissociation",
        "person",
        "sample",
        "cell_suspension",
        "lib_prep",
        "sequencing",
        "file",
    )
    if s not in EXCLUDED_SHEETS
)


def align(reference: Manifest, test: Manifest) -> Alignment:
    """Align every sheet of two manifests, propagating identity along the graph."""
    result = Alignment()
    for name in ALIGN_ORDER:
        ref_sheet, test_sheet = reference.get(name), test.get(name)
        sheet_alignment = align_sheet(name, ref_sheet, test_sheet, result.id_map)
        result.sheets[name] = sheet_alignment

        key = PRIMARY_KEY.get(name)
        if key and ref_sheet and test_sheet:
            mapping: dict[str, str] = {}
            for pair in sheet_alignment.pairs:
                ref_id = ref_sheet.rows[pair.ref_index].get(key, "")
                test_id = test_sheet.rows[pair.test_index].get(key, "")
                if ref_id and test_id:
                    mapping[ref_id] = test_id
            result.id_map[name] = mapping
    for name in SCORED_SHEETS:
        result.sheets.setdefault(name, SheetAlignment(sheet=name))
    return result
