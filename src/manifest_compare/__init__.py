"""Compare manifests extracted from the same manuscript by different annotators.

Given two spreadsheet manifests of one paper -- one curated by a human, one
produced by a language model -- work out how closely the second reproduces the
first, without mistaking presentational differences for disagreements.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .align import align
from .compare import Outcome, PairResult, compare_manifests
from .io import Manifest, load_manifest
from .report import corpus_report, scorecard, write_reports

__all__ = [
    "__version__",
    "align",
    "compare_manifests",
    "corpus_report",
    "load_manifest",
    "Manifest",
    "Outcome",
    "PairResult",
    "scorecard",
    "write_reports",
]
