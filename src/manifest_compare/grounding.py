"""Is a recorded value traceable to the manuscript it was supposedly read from?

Both manifests are meant to be extractions: every value should come from the
paper. That is checkable without a model. Fold the PDF text with the same
normaliser used on the manifests -- the Cao paper writes `10x Genomics Chromium
Single-Cell 3'kit` with a multiplication sign and a curly quote, and a raw
substring search misses it -- then ask how much of each value's distinctive
vocabulary appears in the text.

This answers a question the manifest comparison cannot: when the two annotators
disagree, is either of them talking about the paper? And when one fills a field
the other left blank, did they read it or invent it?

What it cannot do is prove fabrication. A curator writing `Laboratory` for
`env_broad_scale` is making a reasonable inference from a paper that never uses
the word, and a value drawn from a supplement will look identical to one invented
outright. Values too short to carry distinctive vocabulary are therefore reported
as not assessable rather than counted either way.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .normalise import fold
from .schema import FieldClass, classify

#: Tokens shorter than this carry no evidential weight.
MIN_TOKEN_LENGTH = 3

#: A value needs at least this many distinctive tokens to be assessable.
MIN_DISTINCTIVE = 2

#: Share of distinctive tokens that must appear in the paper.
GROUNDED_AT = 0.80
PARTIAL_AT = 0.40

_WORD = re.compile(r"[a-z0-9]+")

#: Words too common in this literature to evidence anything.
NOISE: frozenset[str] = frozenset(
    """the a an of and or for with in on at to by from as was were is are be been
    that this it its their které which we our using used single cell cells sample
    samples data analysis study performed use also can may than then these those
    all any each per via into out over under between during after before not no
    protocol method methods kit type types number total high low new one two both
    plant plants gene genes""".split()
)


class Grounding(str, Enum):
    VERBATIM = "verbatim"
    """The value appears in the paper essentially word for word."""

    GROUNDED = "grounded"
    """Nearly all of the value's distinctive vocabulary appears in the paper."""

    PARTIAL = "partial"
    """Some of it appears; the value may be a paraphrase or a mix."""

    UNSUPPORTED = "unsupported"
    """Little of it appears. Inferred, drawn from elsewhere, or invented."""

    NOT_ASSESSABLE = "not_assessable"
    """Too short or too generic to judge -- e.g. 'Root', 'Laboratory'."""


@dataclass(frozen=True)
class GroundingResult:
    sheet: str
    column: str
    field_class: FieldClass
    value: str
    grounding: Grounding
    coverage: float
    missing_tokens: tuple[str, ...] = ()


def read_pdf(path: str | Path) -> str:
    """Extract and fold a PDF's full text."""
    import fitz

    document = fitz.open(str(path))
    try:
        raw = "\n".join(page.get_text() for page in document)
    finally:
        document.close()
    return fold(raw)


class PaperText:
    """A paper's folded text, with a cached token set for fast lookup."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.tokens = frozenset(_WORD.findall(text))

    @classmethod
    def from_pdf(cls, path: str | Path, cache_dir: str | Path | None = None) -> "PaperText":
        """Load a paper, caching the extracted text beside a hash of the file.

        Extraction is deterministic, so the cache is keyed on the PDF's own bytes:
        a re-run over an unchanged corpus never re-parses anything.
        """
        path = Path(path)
        if cache_dir is None:
            return cls(read_pdf(path))
        cache = Path(cache_dir)
        cache.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:32]
        cached = cache / f"{digest}.txt"
        if cached.exists():
            return cls(cached.read_text(encoding="utf-8"))
        text = read_pdf(path)
        cached.write_text(text, encoding="utf-8")
        return cls(text)

    def distinctive(self, value: str) -> list[str]:
        """The tokens of a value that could evidence its presence in a paper."""
        return [
            t
            for t in _WORD.findall(fold(value))
            if len(t) >= MIN_TOKEN_LENGTH and t not in NOISE
        ]

    def assess(self, value: str) -> tuple[Grounding, float, tuple[str, ...]]:
        """Classify how far a value is traceable to this paper."""
        folded = fold(value)
        if folded and folded in self.text:
            return Grounding.VERBATIM, 1.0, ()
        tokens = self.distinctive(value)
        if len(set(tokens)) < MIN_DISTINCTIVE:
            return Grounding.NOT_ASSESSABLE, 0.0, ()
        unique = sorted(set(tokens))
        found = [t for t in unique if t in self.tokens]
        missing = tuple(t for t in unique if t not in self.tokens)
        coverage = len(found) / len(unique)
        if coverage >= GROUNDED_AT:
            return Grounding.GROUNDED, coverage, missing
        if coverage >= PARTIAL_AT:
            return Grounding.PARTIAL, coverage, missing
        return Grounding.UNSUPPORTED, coverage, missing


def assess_manifest(manifest, paper: PaperText) -> list[GroundingResult]:
    """Assess every populated, non-surrogate value in a manifest."""
    from .schema import SCORED_SHEETS

    results: list[GroundingResult] = []
    for name in SCORED_SHEETS:
        sheet = manifest.get(name)
        if not sheet:
            continue
        for row in sheet.rows:
            for column, value in row.items():
                if not value or classify(column) is FieldClass.SURROGATE:
                    continue
                grounding, coverage, missing = paper.assess(value)
                results.append(
                    GroundingResult(
                        name, column, classify(column), value,
                        grounding, round(coverage, 3), missing[:6],
                    )
                )
    return results
