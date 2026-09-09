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
