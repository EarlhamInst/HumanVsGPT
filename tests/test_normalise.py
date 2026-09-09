"""Normalisation is where most false disagreements are prevented or created."""

from manifest_compare.normalise import (
    accessions, canonical, fold, normalise_column, quantity,
)


def test_fold_maps_unicode_confusables_seen_in_the_corpus():
    # The papers and manifests use a multiplication sign in '10x' and a curly
    # quote in "3'", so a raw comparison reports a difference that is not one.
    assert fold("10× Genomics Chromium Single-Cell 3’kit") == (
        "10x genomics chromium single-cell 3'kit"
    )
    assert fold("Vukašinović") == "vukasinovic"
    assert fold("cell type–specific") == "cell type-specific"


def test_normalise_column_strips_the_optional_marker():
    assert normalise_column("suspension_volume_µl (optional)") == "suspension_volume_ul"
    assert normalise_column("study_id") == "study_id"


def test_canonical_unifies_controlled_terms():
    assert canonical("suspension_type", "Protoplast suspension") == "protoplast"
    assert canonical("suspension_type", "protoplast") == "protoplast"
    assert canonical("lib_layout", "PAIRED") == canonical("lib_layout", "Paired-end")
    assert canonical("primeness", "3'") == "3-prime"


def test_canonical_leaves_unmapped_values_alone():
    assert canonical("suspension_type", "something novel") == "something novel"


def test_accessions_are_extracted_from_running_prose():
    # Both manifests bury accessions in sentences, and in different columns, so
    # extraction has to work on the text rather than on whole-cell equality.
    found = accessions("Data at NCBI SRA BioProject PRJNA865791; GEO GSE185068")
    assert found["bioproject"] == frozenset({"PRJNA865791"})
    assert found["geo_series"] == frozenset({"GSE185068"})


def test_accessions_returns_nothing_for_prose_without_one():
    assert accessions("protoplasts were isolated enzymatically") == {}


def test_quantity_parses_the_forms_present_in_the_corpus():
    assert quantity("27.0") == (27.0, "")
    assert quantity("26 °C") == (26.0, "degc")
    assert quantity("5-mm root tips") == (5.0, "")
    assert quantity("not a number at all") is None
