"""Field comparison: the seven outcomes, on values taken from the corpus."""

from manifest_compare.compare import Outcome, compare_field


def outcome(sheet, column, reference, test):
    return compare_field(sheet, column, reference, test).outcome


def test_a_typo_in_the_reference_is_not_a_disagreement():
    # The human Cao manifest records 'llumina NovaSeq 6000' -- a dropped capital
    # I. Calling that a conflict would be a finding about the reference's typing.
    assert outcome(
        "sequencing", "sequencing_instrument_model",
        "llumina NovaSeq 6000", "Illumina NovaSeq 6000",
    ) is Outcome.EQUIVALENT


def test_a_real_numeric_difference_is_a_conflict():
    assert outcome("sample", "temp", "27.0", "26 °C") is Outcome.CONFLICT


def test_the_same_quantity_written_differently_is_equivalent():
    assert outcome("sample", "temp", "26", "26 °C") is Outcome.EQUIVALENT


def test_controlled_terms_are_compared_after_canonicalisation():
    assert outcome(
        "cell_suspension", "suspension_type", "protoplast", "Protoplast suspension"
    ) is Outcome.EQUIVALENT


def test_elaboration_is_recognised_however_low_the_overlap():
    # 'Root' inside 'Primary root tip containing root cap...' is the same fact
    # elaborated; token overlap is only 0.12, so containment has to decide it.
    assert outcome(
        "sample", "tissue", "Root",
        "Primary root tip containing root cap, meristem and elongation zone",
    ) is Outcome.TEST_MORE_SPECIFIC


def test_losing_detail_counts_against_the_test_manifest():
    assert outcome(
        "sequencing", "sequencing_platform_name", "Illumina NovaSeq", "Illumina"
    ) is Outcome.TEST_LESS_SPECIFIC


def test_a_blank_test_value_is_missing_not_wrong():
    assert outcome("file", "read_1_file", "SRR21124421", "") is Outcome.MISSING_IN_TEST


def test_a_blank_reference_value_is_unknown_not_false():
    # Scored in neither metric: it goes to the adjudication queue instead.
    assert outcome(
        "study", "associated_resource", "", "NCBI SRA BioProject PRJNA865791"
    ) is Outcome.TEST_ONLY


def test_two_blanks_are_not_a_comparison():
    assert outcome("sample", "tissue", "", "") is Outcome.BOTH_ABSENT


def test_a_maker_against_its_machine_is_specificity_not_conflict():
    # 'NextSeq 500' and 'Illumina' agree as far as either goes; token
    # containment cannot see it, because 'Illumina' is not a word in
    # 'NextSeq 500'.
    assert outcome(
        "sequencing", "sequencing_platform_name", "NextSeq 500", "Illumina"
    ) is Outcome.TEST_LESS_SPECIFIC
    assert outcome(
        "sequencing", "sequencing_platform_name", "Illumina", "DNBSEQ-T7"
    ) is Outcome.CONFLICT  # different makers really do disagree


def test_two_bare_maker_names_agree():
    assert outcome(
        "sequencing", "sequencing_platform_name", "Illumina", "illumina"
    ) is Outcome.EQUIVALENT


def test_the_same_citation_in_two_formats_is_not_a_conflict():
    # Identifier-class fields carry the heaviest weight in the score, so calling
    # two formats of one reference a disagreement is expensive and wrong.
    assert outcome(
        "dissociation", "literature_source_reference",
        "Bargmann & Birnbaum, J. Vis. Exp. 2010; PMID 20168296",
        "Bargmann B.O.R. and Birnbaum K.D. (2010). Fluorescence activated cell "
        "sorting of plant protoplasts. Journal of Visualized Experiments 36:1673.",
    ) is Outcome.EQUIVALENT


def test_different_works_still_conflict():
    assert outcome(
        "dissociation", "literature_source_reference",
        "Smith et al. 2019", "Jones et al. 2021",
    ) is Outcome.CONFLICT


def test_version_notation_is_not_a_disagreement():
    for reference, test in (("v4", "4"), ("V3", "version 3"), ("v1.1", "1.1")):
        assert outcome(
            "lib_prep", "library_prep_kit_version", reference, test
        ) is Outcome.EQUIVALENT
    assert outcome(
        "lib_prep", "library_prep_kit_version", "v2", "v3"
    ) is Outcome.CONFLICT


def test_yes_no_notation_is_not_a_disagreement():
    for reference, test in (("none", "No"), ("N/A", "no"), ("Yes", "true")):
        assert outcome("lib_prep", "spike_in", reference, test) is Outcome.EQUIVALENT
    assert outcome("lib_prep", "spike_in", "yes", "none") is Outcome.CONFLICT
