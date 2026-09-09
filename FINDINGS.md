# Essential to report

A working list of what the write-up must contain, kept alongside the code so it
stays tied to the analysis that produced it. Items are marked **established**
(supported by the current analysis), **provisional** (a lead, not yet
substantiated) or **open** (still to be decided or done).

Figures below come from 21 paired manifests, 6,487 field comparisons, at commit
`cdd752f`. They will move as adjudication proceeds and must be regenerated
before publication.

---

## 1. Headline findings

**1.1 GPT is the more diligent annotator per field, and the less reliable one
per entity.** *(established)*

* higher fill rate in **19 of 21** papers -- mean 48.1% against the human's
  37.8%, a 1.27x ratio
* but records **fewer rows**: 665 against 862 across the corpus, 0.77x
* the two effects nearly cancel in total fields filled (4,910 against 4,865,
  1.01x), so any aggregate coverage figure conceals them

Mendieta is the clearest case: GPT filled nearly three times as much of each row
while recording 26 rows against the human's 98. Reporting only one of these
numbers would misdescribe the result.

Mechanistically these are different tasks. Filling columns is description --
the methods section is present and GPT transcribes it well. Enumerating rows is
bookkeeping -- inferring that two genotypes by two treatments by two replicates
means eight samples, from information spread across a figure legend and a data
availability statement.

**1.2 The dominant failure is omission, not error.** *(established)*
`missing_in_test` is the largest single outcome at 36.9% of all comparisons.
Precision (69.7%) far exceeds recall (43.6%), and the gap is entirely the cost
of GPT's silences.

**1.3 GPT is not fabricating.** *(established)* Of the 1,622 fields GPT filled
where the human was silent -- 25% of all comparisons, scored in neither metric --
**74.8%** of assessable values are traceable to the paper and only **1.3%** are
unsupported. Its extra coverage is largely real content the human did not record.

**1.4 The reference is wrong often enough to matter.** *(established)* Of 459
conflicts, 100 have the human grounded in the paper and GPT not, but **64 are
the other way round** -- roughly one disagreement in seven where the reference is
the weaker answer. Every one of those currently scores against GPT.

**1.5 Numeric fields are the weak class.** *(established)* 12.1% recall against
45.7% for prose. Quantities -- cell counts, viabilities, volumes, cycle numbers --
are omitted far more than narrative content.

**1.6 GPT's `temp` field is the one real invention candidate.** *(provisional)*
20 of GPT's 63 unsupported values are growth temperatures in papers that state
none. Numbers cannot be paraphrase or inference in the way prose can. Needs
checking case by case before it is reported as fabrication.

---

## 2. Caveats that must be reported

These are not optional. Several of them change how the headline numbers should
be read, and a reviewer will find them.

**2.1 The reference is unvalidated.** Precision is a **floor**, not a
measurement: it counts agreement with one human curator, and every disagreement
is charged to GPT even where the human is demonstrably wrong (see 1.4).

**2.2 25% of comparisons are scored in neither metric.** A blank reference cell
means *unknown*, not *false*, so fields GPT filled and the human left blank go to
adjudication rather than into recall or precision.

**2.3 Grounding detects absence from a document, not invention.** It cannot
distinguish invented from looked-up, inferred, or correctly paraphrased. Of the
57 human values it flags as unsupported, six are ORCIDs the curator looked up --
no paper prints them -- most of the rest are standard terminology the paper words
differently or controlled-vocabulary inference such as `Eukaryota; Viridiplantae`,
and only two are actual defects. The residual is **not** a fabrication rate.

**2.4 Verbatim-versus-paraphrase confound.** The human copies (65.2% of values
verbatim from the paper); GPT rephrases (35.2%). Grounding rewards matching the
paper's vocabulary, so part of the human's apparent advantage (93.7% against
84.4%) is stylistic rather than substantive.

**2.5 Mean and pooled figures differ substantially** -- recall 43.6% by paper
against 29.3% pooled by field -- because the papers with most fields are those
GPT handled worst. Report both; neither is "the" number.

**2.6 Five pairs were quarantined and the criterion must be stated.** The human
manifests contained blocks of rows identical in content and parentage, differing
only by an auto-incremented ID. `pca_manifest_marchant_2025.xlsx` declares 2182
maize anther samples all reading the same values, against GPT's 11. Including
them raised the denominator so far that corpus row coverage read 7.0% instead of
58.0%.

**2.7 About a quarter of matched rows are ambiguously aligned** (26.7%), mostly
where the human manifest omits the field distinguishing replicates. In Cao the
sample sheet records genotype but never inoculation treatment, so the eight
samples cannot be told apart.

**2.8 Main text only; no supplementary material.** Both annotators are
understood to have worked from the same PDFs. *(open -- see 4.1)*

**2.9 Adjudication is incomplete.** 90 of 449 conflicts settled at the time of
writing. Any accuracy claim derived from conflicts is provisional until the
queue is worked.

---

## 3. Findings about the schema, not the annotators

Three fields produced disagreement because the PCA template does not define them
tightly enough for two careful readers to agree. These should be reported to the
template maintainers and are arguably a more actionable result than the scores.

**3.1 `input_molecule` is undefined** *(established)* -- 65 conflicts, 14% of the
whole conflict queue. Resolved here as the molecule that reaches the sequencer
(the cDNA library). Critically, **the human curators were not internally
consistent**: some wrote `cDNA`, others `mRNA` or `poly(A)+ RNA`, for the same
10x chemistry. In 13 cases both annotators named the capture input, so under the
adopted definition neither is correct.

**3.2 `tax_class` does not say whether it wants an identifier or a label**
*(established)* -- 9 conflicts, e.g. `381124` against `Liliopsida`. These are the
same fact; 381124 *is* the NCBI taxon ID for Liliopsida.

**3.3 The free-text protocol fields do not state the intended granularity**
*(established)* -- `dissociation_description`, `protocol_name`,
`single_cell_quality_metric`, `workflow`. One annotator records the method
category, the other transcribes the procedure with reagents and concentrations.
Both are faithful; the schema never says which is wanted.

**3.4 Some fields are curator-assigned labels, not extracted facts**
*(established)* -- `protocol_name`, `samp_name`. Grounding against the manuscript
is not a meaningful test for these, and scoring disagreement between two valid
labels is not measuring extraction quality.

---

## 4. Open questions

**4.1 Did the human curators have supplementary material GPT did not?**
*(provisional)* The Cao paper defers protocol detail explicitly -- *"protoplast
counting and viability assessment are available in Appendix S1"* -- and the human
manifest records a viability method (`fluorescence-diacetate`, `hemocytometer`)
whose terms are absent from the main text. One instance only; it survived
correction of two grounding bugs, so it is not an artifact. If the human worked
from paper plus supplement and GPT from paper alone, part of the recall gap
measures an asymmetry of evidence rather than of ability. **This needs settling
before publication.**

**4.2 Two papers buck the fill-rate trend** -- Liu (human 59%, GPT 42%) and
Vukašinović (53%, 49%) -- and in both GPT also recorded far fewer rows. Worth
checking whether GPT partly gave up on these.

**4.3 `description` and `design_description` conflicts are unadjudicated** -- 33
cases of genuine editorial variation, where two faithful summaries differ.

---

## 5. Method transparency

Report these; they affect how much weight the grounding figures carry.

**5.1 Two false-negative bugs were found and fixed in the grounding check, both
biased against detailed values.** PDF typesetting hyphenates across line breaks
(`cy-cles`), and no allowance was made for inflection (`protoplasts` against
`protoplast`). Correcting them moved human grounding 90.9% -> 93.7% and GPT
80.1% -> 84.4%. GPT gained more, as expected. **The corrected figures remain a
floor**: there will be further false negatives not yet found.

**5.2 One comparison bug was fixed rather than adjudicated.** A manufacturer
against one of its instruments (`Illumina` against `NextSeq 500`) was scoring as
a contradiction rather than a difference of specificity; token containment could
not see it because "Illumina" is not a word in "NextSeq 500". Reclassified 10
conflicts.

**5.3 Referential integrity is deliberately not checked.** These manifests are
unvalidated extractions; a dangling foreign key is a spreadsheet defect, not a
misreading. The `file` sheet is excluded for a related reason: neither annotator
recorded real raw-file entries.

**5.4 Row matching is content-based and order-independent**, using optimal
assignment with propagation along the entity graph. State this: a positional or
identifier-based comparison of these manifests would report near-total
disagreement between documents that largely agree.

**5.5 All thresholds and weights are recorded in `out/run.json`** alongside input
SHA-256s, so any cut-off can be inspected rather than inferred.

---

## 6. Suggested framing

The useful conclusion is not a single accuracy score. It is a division of
labour: **GPT is a strong first-pass populator and a weak enumerator.** The row
skeleton -- how many samples, libraries and runs -- is better established by a
human or by a script reading the SRA/GEO record; GPT is then good at filling it.
