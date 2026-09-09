"""Rulings settle classes of conflict; verdicts settle single fields."""

from manifest_compare.adjudication import Ruling, Verdict, Verdicts
from manifest_compare.compare import FieldResult, Outcome
from manifest_compare.schema import FieldClass


def conflict(column, reference, test, sheet="lib_prep"):
    return FieldResult(
        sheet, column, FieldClass.VOCAB, Outcome.CONFLICT, reference, test
    )


INPUT_MOLECULE = Ruling(
    id="input_molecule_is_sequenced_molecule",
    column="input_molecule",
    verdict="reference",
    reference_pattern="^(cdna|complementary dna)$",
    test_pattern="rna",
    rationale="the sequenced molecule is the cDNA library",
)


def test_a_ruling_matches_regardless_of_case_and_phrasing():
    verdicts = Verdicts(rulings=[INPUT_MOLECULE])
    for test_value in ("RNA", "polyadenylated RNA", "Polyadenylated messenger RNA"):
        decision, source, _ = verdicts.decide("any paper", conflict("input_molecule", "cDNA", test_value))
        assert decision is Verdict.REFERENCE
        assert source == "ruling:input_molecule_is_sequenced_molecule"


def test_a_ruling_does_not_reach_beyond_its_pattern():
    verdicts = Verdicts(rulings=[INPUT_MOLECULE])
    # The human wrote an RNA term too, so this is not the case the ruling decides.
    decision, _, _ = verdicts.decide("any", conflict("input_molecule", "mRNA", "polyadenylated RNA"))
    assert decision is Verdict.UNDECIDED


def test_granularity_conditions_restrict_a_ruling_to_the_right_shape():
    # A ruling keyed on column alone would absorb genuine errors in that field.
    ruling = Ruling(
        id="label_vs_transcription", column="dissociation_description",
        verdict="both", reference_max_words=8, test_min_words=20,
        rationale="category label against transcribed protocol",
    )
    verdicts = Verdicts(rulings=[ruling])
    long_test = " ".join(["word"] * 25)
    assert verdicts.decide("p", conflict("dissociation_description", "Enzyme-based dissociation", long_test))[0] is Verdict.BOTH
    # Two short values disagreeing are not this pattern and stay undecided.
    assert verdicts.decide("p", conflict("dissociation_description", "Enzyme-based", "Mechanical"))[0] is Verdict.UNDECIDED


def test_an_item_verdict_overrides_a_ruling():
    verdicts = Verdicts(
        rulings=[INPUT_MOLECULE],
        items={("paper", "lib_prep", "input_molecule", "cDNA", "RNA"): ("both", "checked")},
    )
    decision, source, note = verdicts.decide("paper", conflict("input_molecule", "cDNA", "RNA"))
    assert decision is Verdict.BOTH and source == "verdict" and note == "checked"
