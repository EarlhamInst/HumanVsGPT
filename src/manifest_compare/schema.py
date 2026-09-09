"""Structure and field semantics of the PCA single-cell manifest workbook.

The manifest is an eight-sheet Excel workbook describing a single-cell study,
from the publication down to the raw sequencing files. This module encodes two
things the comparison depends on:

1. The *entity graph* -- which sheet references which, via which column. Used
   solely to propagate row alignment between sheets: once samples are paired,
   the suspensions hanging off them can be paired too. Integrity of these keys
   is never checked -- these manifests are unvalidated extractions, and a
   dangling key is a spreadsheet defect, not an extraction error.
2. The *field class* of every column -- how a value in that column may legitimately
   be compared. A cell-by-cell string diff is meaningless across most of these.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

SHEETS: tuple[str, ...] = (
    "study",
    "person",
    "sample",
    "dissociation",
    "cell_suspension",
    "lib_prep",
    "sequencing",
    "file",
)


class FieldClass(str, Enum):
    """How a column's values may be compared."""

    SURROGATE = "surrogate"
    """Internal identifier (sample_id, library_prep_id...). Arbitrary by nature:
    'cao_2023_s1' and 'SAMPLE_QI319_FV_REP1' denote the same sample. Never scored
    for content; used only to resolve the entity graph."""

    IDENTIFIER = "identifier"
    """Externally resolvable accession (SRR, GEO, BioProject, DOI, ORCID, taxon ID).
    Objectively right or wrong, so compared by exact match after normalisation and
    weighted most heavily."""

    VOCAB = "vocab"
    """Controlled term. Compared after mapping onto a canonical value, so
    'protoplast' == 'Protoplast suspension' and 'Paired-end' == 'PAIRED'."""

    NUMERIC = "numeric"
    """Quantity, optionally with a unit. Parsed and compared with tolerance so
    '27.0' and '26 degC' register as a genuine conflict rather than a string diff."""

    TEXT = "text"
    """Free prose. Never string-compared; scored by token-set containment for
    specificity, and optionally referred to an adjudicator."""


# --- Entity graph ------------------------------------------------------------

@dataclass(frozen=True)
class Link:
    """A foreign-key reference from one sheet to another."""

    from_sheet: str
    column: str
    to_sheet: str
    to_column: str


LINKS: tuple[Link, ...] = (
    Link("person", "study_id", "study", "study_id"),
    Link("sample", "study_id", "study", "study_id"),
    Link("dissociation", "study_id", "study", "study_id"),
    Link("cell_suspension", "study_id", "study", "study_id"),
    Link("cell_suspension", "sample_id", "sample", "sample_id"),
    Link("cell_suspension", "dissociation_protocol_id", "dissociation", "dissociation_protocol_id"),
    Link("lib_prep", "study_id", "study", "study_id"),
    Link("lib_prep", "cell_suspension_id", "cell_suspension", "cell_suspension_id"),
    Link("sequencing", "study_id", "study", "study_id"),
    Link("sequencing", "library_prep_id", "lib_prep", "library_prep_id"),
    Link("file", "study_id", "study", "study_id"),
    Link("file", "library_prep_id", "lib_prep", "library_prep_id"),
    Link("file", "sequencing_id", "sequencing", "sequencing_id"),
)

PRIMARY_KEY: dict[str, str] = {
    "study": "study_id",
    "sample": "sample_id",
    "dissociation": "dissociation_protocol_id",
    "cell_suspension": "cell_suspension_id",
    "lib_prep": "library_prep_id",
    "sequencing": "sequencing_id",
    "file": "file_id",
}

# Sheets holding one row per study rather than one row per entity.
SINGLETON_SHEETS: frozenset[str] = frozenset({"study", "dissociation"})

#: Sheets excluded from comparison entirely.
#:
#: The `file` sheet is meant to list the raw sequencing files of each library --
#: names and checksums. Neither annotator recorded real ones. Where it is
#: populated at all it holds run accessions borrowed from `sequencing`, and it is
#: as often empty or absent. Scoring it would measure a convention neither side
#: was following rather than how well the paper was read, so it is dropped before
#: alignment rather than counted as a failure on either side.
EXCLUDED_SHEETS: frozenset[str] = frozenset({"file"})

#: The sheets actually compared.
SCORED_SHEETS: tuple[str, ...] = tuple(s for s in SHEETS if s not in EXCLUDED_SHEETS)


# --- Field classification ----------------------------------------------------

SURROGATE_COLUMNS: frozenset[str] = frozenset(
    {
        "study_id",
        "sample_id",
        "dissociation_protocol_id",
        "cell_suspension_id",
        "library_prep_id",
        "sequencing_id",
        "file_id",
    }
)

IDENTIFIER_COLUMNS: frozenset[str] = frozenset(
    {
        "orcid_id",
        "accession_number",
        "samp_taxon_id",
        "microb_start_taxID",
        "read_1_file",
        "read_2_file",
        "index_1_file",
        "index_2_file",
        "read_1_file_checksum",
        "read_2_file_checksum",
        "index_1_file_checksum",
        "index_2_file_checksum",
        "associated_resource",
        "literature_source_reference",
        "protocols_io_reference",
        "workflow_hub_sop_reference",
    }
)

NUMERIC_COLUMNS: frozenset[str] = frozenset(
    {
        "temp",
        "cell_count",
        "cell_size",
        "suspension_volume_ul",
        "suspension_concentration_cells_per_ul",
        "suspension_dilution",
        "cdna_amplification_cycles",
        "average_size_distribution",
        "umi_barcode_offset",
        "umi_barcode_size",
        "cell_barcode_offset",
        "cell_barcode_size",
        "ph",
        "depth",
        "elev",
    }
)

VOCAB_COLUMNS: frozenset[str] = frozenset(
    {
        "suspension_type",
        "lib_layout",
        "primeness",
        "input_molecule",
        "technology",
        "ploidy",
        "trophic_level",
        "biotic_relationship",
        "tax_class",
        "env_broad_scale",
        "sequencing_platform_name",
        "sequencing_instrument_model",
        "organism",
        "specific_host",
    }
)


def classify(column: str) -> FieldClass:
    """Return the comparison class for a (normalised) column name."""
    if column in SURROGATE_COLUMNS:
        return FieldClass.SURROGATE
    if column in IDENTIFIER_COLUMNS:
        return FieldClass.IDENTIFIER
    if column in NUMERIC_COLUMNS:
        return FieldClass.NUMERIC
    if column in VOCAB_COLUMNS:
        return FieldClass.VOCAB
    return FieldClass.TEXT


# --- Scoring weights ---------------------------------------------------------

#: Relative weight of each field class in the headline agreement score.
#: Accessions make a manifest actionable, so they dominate; prose is scored but
#: contributes least because it is the least objectively checkable.
CLASS_WEIGHTS: dict[FieldClass, float] = {
    FieldClass.IDENTIFIER: 3.0,
    FieldClass.VOCAB: 2.0,
    FieldClass.NUMERIC: 2.0,
    FieldClass.TEXT: 1.0,
    FieldClass.SURROGATE: 0.0,
}

#: Relative weight of each sheet. Sample structure and file accessions are what
#: make a manifest usable for data retrieval; protocol prose matters less.
SHEET_WEIGHTS: dict[str, float] = {
    "study": 1.5,
    "person": 1.0,
    "sample": 2.0,
    "dissociation": 1.0,
    "cell_suspension": 1.0,
    "lib_prep": 1.0,
    "sequencing": 1.5,
}
