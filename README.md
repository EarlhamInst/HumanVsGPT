# HumanVsGPT

How closely does a language model reproduce a human curator's reading of a
scientific paper?

Twenty-one single-cell plant genomics papers were each described twice, by a
human curator and by GPT, using the same eight-sheet metadata manifest. This
repository holds those manifests, the code that compares them, and the record of
how their disagreements were settled.

## The problem with just diffing them

The two manifests agree about the biology and disagree about almost everything
else. They list samples in different orders. They name the same sample
`cao_2023_s1` and `SAMPLE_QI319_FV_REP1`. One writes `protoplast` where the
other writes `Protoplast suspension`, `10× Genomics` with a multiplication sign,
`27.0` against `26 °C`. They record the same fact in different columns. A
cell-by-cell comparison reports near-total disagreement between two documents
that largely agree.

Worse, the human manifest is not ground truth. It contains typos (`llumina
NovaSeq 6000`), and one withheld manifest declares 2182 maize anther samples
that are identical but for an auto-incremented ID. Treating it as correct by
definition would score the model down for being right.

## What this does instead

**Match rows on content before scoring any field.** Row order and identifiers are
ignored; rows are paired by optimal assignment on their content, and the pairing
propagates along the entity graph, so once samples are paired the suspensions
hanging off them can be paired too.

**Compare each field by its kind.** Accessions are extracted and set-compared,
controlled terms mapped to canonical form, quantities parsed with units, prose
judged by token containment. Every field lands in one of seven outcomes.

**Report four figures, not one score.**

| | question |
|---|---|
| recall | of what the human recorded, how much did the model capture? |
| precision | where both spoke, how often did they agree? |
| structural fidelity | are there the right number of rows? |
| coverage | how much did each side fill in at all? |

Coverage is reported and never scored. A manifest can be filled end to end with
plausible invention; a sparse one may be scrupulous. Fields the model filled and
the human left blank are counted in neither metric -- a blank reference cell
means *unknown*, not *false* -- and go to an adjudication queue instead.

**Check both sides against the papers.** `grounding.py` asks whether each
recorded value is traceable to the source PDF, by string matching alone, with no
model involved. This answers what the comparison cannot: whether either
annotator was reading the paper.

## Results so far

Over 21 pairs, 6,487 field comparisons:

* the two manifests **agree on 72.8%** of the fields both annotators completed --
  though that is only 38% of the corpus; in the rest, one annotator was silent
* recall **44.5%**, precision **70.9%**, structural fidelity **71%**
* the model's dominant failure is silence, not error: `missing_in_test` is the
  largest single outcome at 36.9%
* both manifests are overwhelmingly grounded in their papers -- **94.0%** human,
  **84.9%** GPT of assessable values. Of the human values that are not, almost
  none are errors: they are ORCIDs looked up externally, standard terminology
  the paper words differently, and controlled-vocabulary inferences such as
  `Eukaryota; Viridiplantae`. Grounding detects absence from the document, not
  invention
* of the 1,622 fields the model filled where the human was silent, **74.8%** are
  traceable to the paper and only **1.3%** are unsupported. The model's extra
  coverage is largely real content, not invention
* of 422 conflicts, **196 have been adjudicated** -- every one where the grounding
  evidence can discriminate. The most common outcome was that **neither annotator
  was wrong**: 96 both-valid, against 62 to the human, 19 to the model and 20 to
  neither
* **no invention was found on either side.** Every ungrounded value examined by
  hand proved to be a correct answer the checker could not match -- an acronym, a
  paraphrase, an externally looked-up identifier, or compact notation

Precision remains a floor rather than a measurement: the reference is
unvalidated, and 226 conflicts are deliberately left undecided because grounding
gives no signal there. See `FINDINGS.md`.

## Install

```bash
pip install -e ".[fast,pdf,dev]"
```

Both extras are optional. Without `fast` the package uses a pure-Python
assignment solver -- correct but slow on large sheets, and verified against the
SciPy path in the tests. Without `pdf` everything except grounding still runs.

## Use

```bash
# score the corpus
manifest-compare compare comparason_matched/matched_pairs.csv -o out

# one pair
manifest-compare pair <reference.xlsx> <test.xlsx> --paper "Cao et al. 2023"

# apply recorded rulings, and build a worksheet of what is still undecided
manifest-compare adjudicate comparason_matched/matched_pairs.csv \
    --pdf-dir /path/to/pdfs --test-grounded-only

# record a decision from that worksheet
manifest-compare record 1 both --by you@example.org --note "why"
```

`out/run.json` records the inputs and their SHA-256s, the tool version, and
every threshold and weight the verdicts depend on, so a reader who disagrees
with a cut-off can see its value rather than infer it.

## Adjudication

Conflicts are settled as data, not code, under `adjudication/`.

A **ruling** settles a whole class by naming the principle behind it and matches
by pattern -- deciding that `input_molecule` means the molecule reaching the
sequencer settles 65 conflicts at once, and will settle the same question in a
future corpus. A **verdict** settles one field in one paper where no principle
applies. Both carry their rationale and who decided, so a reader can see which
calls were general and which case-by-case.

Three of the rulings so far record a finding about the *schema* rather than
about either annotator: `input_molecule`, `tax_class` and the free-text protocol
fields are not defined tightly enough for two careful readers to agree.

## Layout

```
src/manifest_compare/   schema, normalisation, loading, alignment,
                        comparison, grounding, triage, adjudication, reporting
comparason_matched/     the 21 paired manifests, and which paper each describes
quarantine_degenerate/  5 pairs withheld, with the reason
adjudication/           rulings.json, verdicts.csv
tests/
```

## Reproducing

Everything except grounding runs from this repository alone. Grounding needs the
21 source PDFs, which are not distributed here; they are named in
`comparason_matched/paper_pdfs.csv`.

## Licence

MIT for the code and the adjudication decisions. The manifests are derived
metadata from third-party publications and are not licensed by this repository --
see `LICENSE` and `comparason_matched/README.md`.
