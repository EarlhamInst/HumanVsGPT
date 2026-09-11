"""Value normalisation: the layer that decides when two spellings mean one thing.

Every non-trivial finding in the Cao comparison came down to normalisation. The
two manifests write the same facts as '10x Genomics Chromium Single Cell 3'' and
'10x Genomics Chromium Single-Cell 3'kit'; as 'protoplast' and 'Protoplast
suspension'; as '27.0' and '26 degC'. Comparing raw strings would call all three
disagreements. Comparing over-aggressively would hide the third, which is a real
factual conflict.
"""

from __future__ import annotations

import re
import unicodedata

# Unicode confusables seen across the corpus: curly quotes, the multiplication
# sign in '10x Genomics', en/em dashes in 'cell type-specific', the prime in 3'.
_PUNCT_MAP = {
    "‘": "'", "’": "'", "ʼ": "'", "′": "'",
    "“": '"', "”": '"',
    "‐": "-", "‑": "-", "‒": "-", "–": "-",
    "—": "-", "―": "-", "−": "-",
    "×": "x", " ": " ",
    "µ": "u", "μ": "u",
}

_COLUMN_SUFFIX = re.compile(r"\s*\(optional\)\s*$", re.I)


def normalise_column(name: str) -> str:
    """Strip the '(optional)' marker and unify case/spacing in a column header."""
    if name is None:
        return ""
    out = _COLUMN_SUFFIX.sub("", str(name)).strip()
    for bad, good in _PUNCT_MAP.items():
        out = out.replace(bad, good)
    return out.replace(" ", "_")


def fold(value: object) -> str:
    """Fold a cell value to a comparable form: NFKD, confusables mapped, cased down.

    Preserves word content and internal punctuation so that specificity
    comparisons still work; only presentation differences are erased.
    """
    if value is None:
        return ""
    text = str(value).strip()
    for bad, good in _PUNCT_MAP.items():
        text = text.replace(bad, good)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip().lower()


_TOKEN = re.compile(r"[a-z0-9]+")


def tokens(value: object) -> frozenset[str]:
    """Content tokens of a value, for set-containment (specificity) tests."""
    return frozenset(_TOKEN.findall(fold(value))) - STOPWORDS


STOPWORDS: frozenset[str] = frozenset(
    {"the", "a", "an", "of", "and", "or", "for", "with", "in", "on", "at", "to",
     "by", "from", "as", "was", "were", "is", "are", "be", "been", "that", "this",
     "kit", "using", "used", "single", "cell", "cells"}
)


# --- Controlled vocabulary ---------------------------------------------------

#: Maps a folded value onto a canonical term, per column. Deliberately small and
#: explicit: an over-broad synonym table would mask real disagreements.
VOCAB: dict[str, dict[str, str]] = {
    "suspension_type": {
        "protoplast": "protoplast",
        "protoplasts": "protoplast",
        "protoplast suspension": "protoplast",
        "single-cell protoplast suspension": "protoplast",
        "nucleus": "nucleus",
        "nuclei": "nucleus",
        "single nuclei": "nucleus",
        "nuclei suspension": "nucleus",
        "cell": "cell",
        "single cell suspension": "cell",
    },
    "lib_layout": {
        "paired": "paired", "paired-end": "paired", "pe": "paired",
        "paired end": "paired",
        "single": "single", "single-end": "single", "se": "single",
    },
    "primeness": {
        "3'": "3-prime", "3": "3-prime", "3 prime": "3-prime",
        "3-prime": "3-prime", "3' end": "3-prime",
        "3-prime transcript capture": "3-prime",
        "5'": "5-prime", "5": "5-prime", "5 prime": "5-prime",
        "5-prime": "5-prime",
    },
    "input_molecule": {
        "cdna": "cdna", "rna": "rna", "polya rna": "mrna",
        "polyadenylated messenger rna": "mrna", "mrna": "mrna",
        "dna": "dna", "genomic dna": "dna",
    },
    # The answer to this field is literally the word "single" or "dual", which
    # collides with the stopword list: "single" is noise in "single cell" and the
    # entire signal here. Treating the field as the closed vocabulary it is
    # sidesteps that, and is what a validated template would have enforced.
    "dual_single_index": {
        "single": "single", "single index": "single", "si": "single",
        "single-index": "single", "single indexing": "single",
        "dual": "dual", "dual index": "dual", "di": "dual",
        "dual-index": "dual", "dual indexing": "dual",
    },
    "ploidy": {"diploid": "diploid", "2n": "diploid", "haploid": "haploid", "1n": "haploid"},
}


#: Sequencing instrument models mapped to their manufacturer.
#:
#: `NextSeq 500` and `Illumina` are not a disagreement -- one names the machine
#: and the other the maker -- but token containment cannot see that, because the
#: word "Illumina" does not appear in "NextSeq 500". Without this the two score
#: as a flat conflict rather than as one annotator being less specific.
INSTRUMENT_MANUFACTURER: dict[str, str] = {
    "novaseq": "illumina", "nextseq": "illumina", "hiseq": "illumina",
    "miseq": "illumina", "miniseq": "illumina", "iseq": "illumina",
    "nextera": "illumina",
    "dnbseq": "mgi", "mgiseq": "mgi", "bgiseq": "bgi",
    "sequel": "pacbio", "revio": "pacbio",
    "promethion": "oxford nanopore", "minion": "oxford nanopore",
    "gridion": "oxford nanopore",
    "ion torrent": "thermo fisher", "proton": "thermo fisher",
}

MANUFACTURERS: frozenset[str] = frozenset(INSTRUMENT_MANUFACTURER.values())


def manufacturer_of(value: object) -> str:
    """The manufacturer a platform value denotes, if it names one at all."""
    folded = fold(value)
    for maker in MANUFACTURERS:
        if maker in folded:
            return maker
    for model, maker in INSTRUMENT_MANUFACTURER.items():
        if model in folded:
            return maker
    return ""


def names_only_manufacturer(value: object) -> bool:
    """True when a value names a maker and no particular machine."""
    folded = fold(value)
    if not folded:
        return False
    maker = manufacturer_of(value)
    if not maker:
        return False
    if any(model in folded for model in INSTRUMENT_MANUFACTURER):
        return False
    return folded.replace(maker, "").strip(" -,;") == ""


#: Ways of writing yes and no. Two manifests recording that no spike-in was used,
#: one as `none` and one as `No`, were otherwise compared as opaque strings and
#: reported as a disagreement about whether a spike-in was used at all.
BOOLEAN: dict[str, bool] = {
    "yes": True, "y": True, "true": True, "present": True, "used": True,
    "no": False, "n": False, "none": False, "not used": False, "false": False,
    "n/a": False, "na": False, "not applicable": False, "nil": False,
    "not used.": False, "no spike-in": False, "no spike in": False,
}


def boolean(value: object) -> bool | None:
    """The yes/no a value denotes, or None if it is not a yes/no answer."""
    return BOOLEAN.get(fold(value).strip(". "))


_VERSION = re.compile(r"^v(?:er(?:sion)?)?[\s.]*([0-9][0-9.]*)$", re.I)


def version_number(value: object) -> str:
    """The bare version a value denotes, if it is only a version.

    `v4`, `V4`, `version 4` and `4` are one version written four ways. Without
    this they are compared as opaque strings and register as a disagreement
    about which kit was used, which is the opposite of what they say.
    """
    folded = fold(value)
    if not folded:
        return ""
    match = _VERSION.match(folded)
    if match:
        return match.group(1)
    return folded if re.fullmatch(r"[0-9][0-9.]*", folded) else ""


def canonical(column: str, value: object) -> str:
    """Canonical form of a controlled-vocabulary value, or the folded value."""
    folded = fold(value)
    return VOCAB.get(column, {}).get(folded, folded)


# --- Identifiers -------------------------------------------------------------

#: Accession patterns that can be verified against a public archive.
ACCESSION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("sra_run", re.compile(r"\b([SED]RR\d{5,})\b", re.I)),
    ("sra_experiment", re.compile(r"\b([SED]RX\d{5,})\b", re.I)),
    ("sra_sample", re.compile(r"\b([SED]RS\d{5,})\b", re.I)),
    ("bioproject", re.compile(r"\b(PRJ[END][AB]\d+)\b", re.I)),
    ("biosample", re.compile(r"\b(SAM[END][AG]?\d+)\b", re.I)),
    ("geo_series", re.compile(r"\b(GSE\d+)\b", re.I)),
    ("geo_sample", re.compile(r"\b(GSM\d+)\b", re.I)),
    ("arrayexpress", re.compile(r"\b(E-[A-Z]{4}-\d+)\b", re.I)),
    ("doi", re.compile(r"\b(10\.\d{4,9}/[^\s,;\"']+)", re.I)),
    ("orcid", re.compile(r"\b(\d{4}-\d{4}-\d{4}-\d{3}[\dX])\b", re.I)),
    ("taxon", re.compile(r"\bNCBI:txid(\d+)\b", re.I)),
)


def accessions(value: object) -> dict[str, frozenset[str]]:
    """Extract every recognisable accession from a value, keyed by kind.

    Free-text fields routinely bury accessions in prose -- GPT recorded the Cao
    BioProject inside a sentence in `associated_resource`. Extracting rather than
    string-matching lets a buried accession still count as captured.
    """
    text = str(value or "")
    found: dict[str, frozenset[str]] = {}
    for kind, pattern in ACCESSION_PATTERNS:
        hits = {m.upper().rstrip(".,;") for m in pattern.findall(text)}
        if hits:
            found[kind] = frozenset(hits)
    return found


# --- Quantities --------------------------------------------------------------

#: A quantity, allowing comma or space thousands separators. Without them
#: `7,000` and `20 000` parse as 7 and 20, so values identical to `7000` and
#: `20000` register as thousandfold disagreements rather than as the same number.
#: Separated groups must be exactly three digits, so `5 mm` and `2 3` are
#: unaffected. The non-breaking space European typesetting uses is already folded
#: to an ordinary space before this runs.
_NUMBER = re.compile(
    r"(-?\d{1,3}(?:[ ,]\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?)"
    r"\s*(?:x\s*10\^?(-?\d+))?\s*([a-z%/_]*)",
    re.I,
)

#: Unit aliases folded to a canonical symbol before comparison.
_UNIT_ALIASES = {
    "c": "degc", "degc": "degc", "degreec": "degc", "celsius": "degc",
    "ul": "ul", "microlitre": "ul", "microliter": "ul",
    "ml": "ml", "l": "l", "bp": "bp", "nt": "nt", "mm": "mm", "cm": "cm",
    "": "",
}


def quantity(value: object) -> tuple[float, str] | None:
    """Parse a value into (magnitude, canonical unit), or None if not numeric.

    Handles the forms actually present in the corpus: bare floats ('27.0'),
    value-with-unit ('26 degC', '5-mm'), and scientific notation.
    """
    text = fold(value)
    if not text:
        return None
    text = text.replace("degrees", "deg").replace("°", "deg")
    match = _NUMBER.search(text)
    if not match:
        return None
    magnitude = float(match.group(1).replace(",", "").replace(" ", ""))
    if match.group(2):
        magnitude *= 10 ** int(match.group(2))
    unit = re.sub(r"[^a-z%]", "", match.group(3) or "")
    return magnitude, _UNIT_ALIASES.get(unit, unit)
