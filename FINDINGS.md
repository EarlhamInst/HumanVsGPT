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

**1.0 Overall agreement: 72.8% of fields both annotators completed -- but that is
38% of the corpus.** *(established)*

Of 6,487 field comparisons, both annotators wrote something in only **2,478**.
Within those:

| | n | share |
|---|---|---|
| agreed (identical, equivalent, or the model more specific) | 1,805 | **72.8%** |
| model less specific (a real loss of detail) | 251 | 10.1% |
| conflicted | 422 | 17.0% |

Two softer readings are also defensible and should be given alongside it:
**76.7%** counting the conflicts adjudicated as both-valid, and **86.8%** also
counting "model less specific", which is thinner but not contradictory.

The figure that must accompany any of these is the denominator. Agreement is
measurable on **38% of the corpus**; in the rest one annotator was silent --
2,387 fields the human filled and the model did not, 1,622 the reverse. Quoting
"they agree about three quarters of the time" without that qualifier
substantially overstates the overlap.

Within the disagreements, the most common adjudicated outcome was that **neither
annotator was wrong**: 96 of 422 conflicts were both-valid, against 81 where one
side won (62 human, 19 model) and 20 where neither did. 225 remain deliberately
undecided (2.13).

**Suggested phrasing.** *The two manifests agree on 72.8% of the fields both
annotators completed. Adjudication of the disagreements found the most common
outcome, 96 of 422, to be that both values were valid. Agreement could be
assessed on only 38% of fields, the remainder having been completed by one
annotator alone.*

And the caveat that governs it: with no second human annotation (2.9), there is
no baseline saying whether 72.8% is high or low. Two human curators might agree
less.

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
Precision (70.9%) far exceeds recall (44.5%), and the gap is entirely the cost
of GPT's silences.

**1.3 The model is not fabricating.** *(established)*

It filled **1,622 fields the human left blank** -- a quarter of all comparisons,
and scored in neither metric, since a blank reference cell means *unknown* rather
than *false*. Checked against the source PDFs: 244 are too short to test (values
such as `Read 1`). Of the 1,378 that can be tested:

| | n | share of testable |
|---|---|---|
| verbatim from the paper | 288 | 20.9% |
| grounded (reworded, key terms present) | 848 | 61.5% |
| partial | 233 | 16.9% |
| **unsupported** | **9** | **0.7%** |

**82.4% trace back to the paper and nine values do not.** The extra coverage is
real content the human did not record. Two consequences: the model's precision
score is an underestimate, since 1,622 largely-correct fields contributed nothing
to it; and the human manifests are less complete than the recall figure implies.

**1.4 The reference is wrong often enough to matter.** *(established)* Of 459
conflicts, 100 have the human grounded in the paper and GPT not, but **64 are
the other way round** -- roughly one disagreement in seven where the reference is
the weaker answer. Every one of those currently scores against GPT.

Treat 64 as an **upper bound**, not a count. Grounding measures vocabulary
overlap, so a value can be grounded and still wrong. In the Yan paper GPT
answered `env_local_scale` with `Rice plant` -- scored `verbatim`, because both
words occur throughout -- while the human answered `Univ of Georgia greenhouse
facility`, scored only `partial`, and was correct: the methods say "rice plants
grown in the greenhouse" and the corresponding author is at Georgia. Grounded but
answering the wrong question is a real failure mode, and adjudication is the only
way to separate it.

**1.5 The two annotators differ in kind, not only in quality: the human applies
expert inference, GPT stays close to the text.** *(established, from
adjudication)*

The human curator routinely records what is conventional but unstated -- `agar`
for a paper that says only "MS plates", `enzymatic` for protoplasting, `Smart-seq2`
where the paper says "well-based Smart-seq" -- and writes in domain shorthand
(`FACS`, `GRN`, pipeline arrows). GPT records what the manuscript actually says,
in the manuscript's own vocabulary, and adds detail the human omits.

This is a defensible difference rather than an error on either side: the audience
for these manifests is necessarily expert and will read "MS plates" as agar
plates. But it has three consequences that must be reported.

* It is invisible to, and penalised by, any text-grounding measure. Inference and
  shorthand share no vocabulary with the paper, so the human's correct-but-unstated
  values score as unsupported (see 2.3, 2.4).
* It is the mechanism behind most of the free-text disagreements. Of the verdicts
  recorded so far the large majority are `both`, and in most of those each
  annotator captured something the other missed -- the human the conventional or
  analytical context, GPT the stated wet-lab detail.
* It means **the two manifests are complementary rather than redundant**. A merged
  manifest would be better than either, which is a more useful conclusion than
  ranking them.

Against that, one adjudicated case went to GPT precisely because the human's
inference over-reached: asserting `Smart-seq2` where the paper says only
"well-based smart-seq protocol", these being distinct chemistries. Expert
inference is usually right and is not always right.

**1.6 Numeric fields are the weakest class, but only for recall -- not for
accuracy.** *(established; revised after three parser fixes)*

| class | n | recall | precision |
|---|---|---|---|
| identifier | 263 | 44.6% | **85.7%** |
| text | 4,010 | 47.4% | 74.1% |
| numeric | 747 | **13.8%** | 78.2% |
| vocab | 1,467 | 26.5% | 64.8% |

Numeric recall is by far the lowest: quantities -- cell counts, viabilities,
volumes, cycle numbers -- are omitted far more often than narrative content. But
numeric **precision is the second highest of any class**. When the model records
a quantity it is usually right; it simply records fewer of them.

An earlier version of this finding reported numeric precision as 68.9%, which was
wrong. Three parser bugs were inflating the conflict count -- compact temperature
notation, and comma and space thousands separators, which made `7,000` and
`20 000` parse as 7 and 20. Correcting them moved numeric precision by more than
nine points, far more than any other class. The recall figure barely moved,
because recall is driven by omission rather than by parsing.

**1.7 No invention has been demonstrated on either side.** *(established; this
replaces an earlier claim that was wrong)*

An earlier version of this list recorded the model's `temp` values as the one
real invention candidate, on the grounds that 20 of its 63 unsupported values
were growth temperatures in papers that appeared to state none. **That claim does
not survive checking and has been withdrawn.**

Every one of those values examined by hand is quoted from its paper. The
Guillotin regime -- "16 h light at 28 C and 8 h dark at 24 C" -- is verbatim, and
it is the *human's* `24` that records only half of it. Bezrutczyk's `28-30 C`,
Turco's `22 C` and Denyer's `22 C` are all stated in their papers too. The
grounding check missed them because papers write temperatures compactly, as
`22c` or `28-30c`, with neither space nor degree sign, and a separate bug parsed
`7,000` as 7.

What the `temp` case actually shows is schema pressure, not fabrication: the
field is singular, plant growth has a day and a night temperature, and the model
answered fully while the human picked one. See 3.5.

Across both adjudication queues -- the 50 conflicts where the model was grounded
and the human was not, and the mirror slice where the reverse holds -- no value
on either side has yet been shown to be invented. Unsupported values have
consistently turned out to be correct answers the checker could not match:
acronyms, paraphrase, external lookups such as ORCIDs, and compact notation.

**This is the single most important correction in the work.** A hallucination
rate was nearly reported, and it would have been an artifact of four separate
false-negative bugs in the measurement, every one of which ran against the more
detailed value.

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
paper's vocabulary, so part of the human's apparent advantage (94.0% against
85.0%) is stylistic rather than substantive.

**2.5 Mean and pooled figures differ substantially** -- recall 44.5% by paper
against 29.7% pooled by field -- because the papers with most fields are those
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

**2.9 There is no inter-annotator baseline, and this may be the study's most
important limitation.**

Almost every disagreement adjudicated so far is of a kind that two human
curators would also produce: how much of a protocol to transcribe, whether to
write `FACS` or spell it out, whether to record the conventional-but-unstated
`agar`, whether `input_molecule` means the captured or the sequenced molecule.
The human curators in this corpus are demonstrably not consistent even with each
other -- some wrote `cDNA` and others `mRNA` for the same chemistry (3.1).

Without a second independent human annotation of the same papers, the study
cannot say whether GPT diverges from a human curator **more than two human
curators diverge from one another**. Every figure here is a human-versus-model
distance with no human-versus-human distance to compare it against, so it cannot
on its own support a claim that the model is worse.

The one place the data does speak is structural: GPT records 0.77x the rows
(1.1). Under-enumeration of samples and runs is not a stylistic difference and
is unlikely to be matched by a careful human. The field-level differences, by
contrast, look like ordinary annotator variation.

**Recommended:** have a second curator annotate a subset -- five or six papers
would do -- and run the identical pipeline on that pair. It would convert most of
this report's figures from uncalibrated distances into interpretable ones, and it
is the first thing a reviewer will ask for.

**Decided: out of scope for this study, and reported as such.** It is a separate
piece of work. The limitation stands and must be stated plainly rather than
worked around; conclusions are framed as descriptions of how the two annotators
differ, not as claims that one is better.

**2.10 Grounding cannot check numeric fields at all.** A bare numeral yields no
distinctive tokens, so a numeric value is `not_assessable`; and where a numeric
value sits inside a sentence, the surrounding words can score it `grounded` while
the number itself -- the entire informational content -- goes unchecked. In the
Yan `lib_size` conflict the human's figure was unassessable and GPT's was scored
grounded on the words around a number the paper never states. Since numeric
fields are also the model's weakest class (1.6), this is a blind spot exactly
where the analysis would most benefit from evidence.

**2.11 A comparison cannot see what both annotators missed.** The method measures
disagreement, so anything omitted by *both* manifests is structurally invisible to
it. Adjudication surfaced one example by accident: on the Conde paper both
annotators recorded the funder and neither recorded the grant number
`DE-SC0018247`, printed in the same sentence, though the manifest has a `funding`
field for it. Shared blind spots of this kind cannot be counted from the present
analysis and would need a separate pass -- for instance, checking each manifest
against a checklist of what the paper states -- to quantify.

**2.12 Grounding cannot validate a correct statement of absence.** Where a paper
reports nothing for a field, the accurate answer is a negative one -- `None
listed` -- and a presence-matching check will always score it poorly, because the
words of a negative claim are by definition not in the document. In the Dorrity
paper the human correctly recorded that no nuclei quality assessment was reported
(no viability stain, trypan blue, DAPI or counting device appears anywhere), and
the model supplied a yield figure instead. The human's value scored `partial`,
the model's `grounded`, and the model's was the one answering a different
question. Expect grounding to be systematically unfair to correct negatives.

**2.13 Adjudication is complete where the evidence discriminates, and
deliberately incomplete elsewhere.**

196 of 422 conflicts are settled. That is not a partial pass at a uniform task:
it is **every conflict in which the grounding evidence can distinguish the two
values**, namely all 66 where the model's value is traceable to the paper and the
human's is not, and all 72 where the reverse holds, plus everything the rulings
reach.

The 226 left are a different problem, not a backlog of the same one:

* **169 have both values grounded.** Both annotators are quoting the paper and
  differ in interpretation, emphasis or granularity. Grounding cannot separate
  them, by construction.
* **56 have neither value grounded**, mostly the inherited MIxS environmental
  fields (3.5) and fields answerable only from the archive (3.8b), where the
  schema permits no right answer.

These were left undecided **on purpose**. Settling them would require adjudicating
either a further 195 cases by hand, or ruling on principles that would decide
them in bulk -- and the candidate principles are not neutral. Four of the five
largest remaining blocks share one shape: the human writes study-level or generic
text where the model writes field-appropriate or row-specific text
(`samp_collect_method`, `experimental_factor`, `description`,
`design_description`). A blanket ruling there would settle roughly 47 conflicts
in the model's favour by decree rather than by evidence, and should not be smuggled
in as a tidying step.

**Report the figure as it stands.** A decided count reached by bulk-ruling a
contested principle, or by a tired reviewer working through 195 judgement calls,
would be less trustworthy than an honest partial count with the remainder
characterised. The unadjudicated conflicts are described above by kind and by
field, which is itself a result: most of what remains is two defensible readings
of the same sentence, or a field that cannot be answered from a manuscript.

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

**3.4 `literature_source_reference` does not specify a citation format**
*(established)* -- one annotator gives an abbreviated citation plus a PMID, the
other a full prose citation from the reference list. Both name the same work.
**Recommendation: the template should require a resolvable identifier (PMID or
DOI)**, which is machine-actionable where a prose citation is not; a free-text
citation may accompany it. Handled in the tool by comparing citations on the work
they name rather than literally.

**3.5 The inherited MIxS/ENA environmental fields do not fit laboratory plant
studies** *(established)* -- `env_local_scale`, `env_broad_scale`, `env_medium`,
`geo_loc_name`. These come from the ENA/MIxS environmental-sampling schema, where
they expect ENVO ontology terms describing where a sample was taken from the
world. For a controlled-environment plant experiment there is often no sensible
answer, and the documentation gives little guidance, so the two annotators
answered differently in kind rather than differently in fact: `Univ of Georgia
greenhouse facility` against `Rice plant`, `Laboratory` against `Controlled
growth cabinet`.

17 `env_local_scale` conflicts corpus-wide, plus further disagreement in the
sibling fields. These are also where the model's unsupported values concentrate
(`temp`, `env_local_scale`, `env_broad_scale`, `env_medium` -- see 1.7), which is
consistent with an annotator inventing plausible answers to a question the paper
never addresses because the schema insists on one.

**Recommendation:** either drop these fields for laboratory studies, or define
their intended values for that case. As they stand they generate disagreement
that measures the schema rather than the annotator.

**Decided: these fields stay in the scoring.** Excluding them would improve the
headline figures by removing a category the annotators genuinely struggled with,
and the struggle is itself part of the result. They are reported as a schema
finding instead.

**3.6 `lib_size` is read in incompatible senses** *(established)* -- the human
recorded `160470000000`, a size in bases; GPT recorded `18 scATAC-seq libraries`,
a count. MIxS defines it as the total number of clones in the library, which
matches neither usage cleanly. Neither value was verifiable in the manuscript.

**3.7 `tax_ident` asks a question that does not arise for these studies**
*(established)* -- in MIxS it holds the phylogenetic marker used to assign an
organism name (16S rRNA gene, multi-marker approach), which is meaningful when
sequencing an unknown environmental sample and not when working with a named
*Arabidopsis* accession. The human answered with NCBI taxon 3702, which belongs
in `samp_taxon_id` and was recorded there too; GPT described the transgenic line
and its GFP selection marker. Neither is taxonomic identification.

**3.8 Some fields are curator-assigned labels, not extracted facts**
*(established)* -- `protocol_name`, `samp_name`. Grounding against the manuscript
is not a meaningful test for these, and scoring disagreement between two valid
labels is not measuring extraction quality.

---

**3.8 Neither manifest was validated, and validation would have prevented about a
third of the disagreement.** *(established)*

131 of 440 conflicts -- **30%** -- occur in fields that are in practice closed
vocabularies, where a validator enforcing the permitted terms would have made the
two annotators agree by construction:

| conflicts | field | example |
|---|---|---|
| 65 | `input_molecule` | `cDNA` vs `RNA` |
| 12 | `technology` | `Single-cell RNA-seq` vs `10x Genomics Chromium 3' single cell` |
| 10 | `cdna_read` | `2` vs a sentence describing the read |
| 9 | `tax_class` | `381124` vs `Liliopsida` |
| 8 | `dual_single_index` | `Single` vs `Single index` |
| 6 | `trophic_level` | `4577` vs `Photoautotroph` |
| 6 | `primeness` | `3 prime` vs `oligo-dT` |

Some are simply wrong in a way a validator catches instantly: `trophic_level`
holding `4577`, which is the NCBI taxon ID for *Zea mays*, and `tax_class` holding
`381124` rather than the name it denotes. These are not disagreements about the
science. One annotator put an identifier where a term belongs and nothing
objected.

**This is the practical recommendation of the whole study.** Much of what looks
like a difference in extraction quality is the absence of a validation step that
would cost little and would constrain human and machine annotators alike. It also
bounds what a comparison like this can measure: against an unvalidated template,
a third of the apparent disagreement is about format rather than content.

**3.8b Some fields cannot be answered from a manuscript at all.** *(established)*
`i7_index` and its siblings expect an actual index sequence, which papers do not
print: the Denyer manuscript contains no ACGT string of index length, no SI-GA
code, and never uses the word "index", naming only the kit in its reagents table.
Both annotators filled the field anyway -- one with the kit name, one with `Yes`
-- and neither value is what the field asks for.

These fields are populated from the sequencing archive submission, not from the
paper. A manifest built by reading manuscripts cannot complete them, and scoring
them measures only which annotator guessed more plausibly. Worth separating in
any future comparison: fields answerable from the text, and fields answerable
only from the archive.

**3.9 Summary: the schema, not the annotators, generates much of the
disagreement.** Seven fields have now been identified where two careful readers
cannot agree because the template does not define what is wanted:
`input_molecule`, `tax_class`, the free-text protocol fields,
`literature_source_reference`, the inherited MIxS environmental fields,
`lib_size` and `tax_ident`. Several are inherited from ENA/MIxS, where they were
designed for environmental sampling and do not transfer to controlled laboratory
plant experiments.

Two failure modes recur. Fields **designed for a different kind of study** have
no sensible answer here, so annotators invent one or answer a neighbouring
question. Fields **left undefined** are read in incompatible senses -- a size
against a count, a label against a transcription, the captured molecule against
the sequenced one.

This may be the most transferable result in the work: a substantial share of what
looks like extraction error is under-specified metadata standards, and it would
affect any annotator, human or machine.

## 4. Open questions

**4.1 The human curators sometimes had supplementary material GPT did not --
real, but rare.** *(established; was open)*

Confirmed on the Cao paper. The human's `dissociation_protocol_method` is a
verbatim supplementary methods protocol: twenty distinctive strings from it
(Gillette, Kimberly-Clark, Sartorius, GoldBio, Onozuka, macerozyme, pectolyase,
W5 solution, specific reagent masses) appear nowhere in the PDF, and the main
text states the protocol is "available in Appendix S1 section of the supporting
information". GPT could not have produced that value from the corpus it was
given.

Scope: a corpus-wide scan finds only **five** long, poorly-grounded human values
across the 21 papers, in five different papers. Four further papers defer to
supplementary material in their main text yet show none, so in most cases the
human worked from the main text as GPT did.

So this is a caveat to state, not a confound that undermines the comparison: it
affects a handful of values, not the 2,393 fields the model did not fill. Report
it, and exclude those values from any claim about relative completeness.

**Caveat on the scan:** it detects only long values, so a supplementary-sourced
number or short phrase would pass unnoticed -- the Cao viability metric
(`fluorescence-diacetate`, `hemocytometer`) is exactly such a case and was found
by hand. Treat five as a lower bound.

**4.2 Two papers buck the fill-rate trend** -- Liu (human 59%, GPT 42%) and
Vukašinović (53%, 49%) -- and in both GPT also recorded far fewer rows. Worth
checking whether GPT partly gave up on these.

**4.3 `description` and `design_description` conflicts are unadjudicated** -- 33
cases of genuine editorial variation, where two faithful summaries differ.

---

**4.4 The model under test was `gpt-5.6-sol`.** *(established)* Manifests were
generated by `extract_metadata_to_manifest.py` in
[EarlhamInst/Scraper_sc](https://github.com/EarlhamInst/Scraper_sc), calling
`gpt-5.6-sol` at temperature 1, one prompt per worksheet. Results here describe
that model and that prompting strategy; they do not generalise to other models,
and the repository's commit dates are not a reliable guide to which model ran,
the switch having been made in the working tree before it was committed.

## 5. Method transparency

Report these; they affect how much weight the grounding figures carry.

**5.1 Two false-negative bugs were found and fixed in the grounding check, both
biased against detailed values.** PDF typesetting hyphenates across line breaks
(`cy-cles`), and no allowance was made for inflection (`protoplasts` against
`protoplast`). Correcting them, and later the acronym and notation fixes, moved
human grounding 90.9% -> 94.0% and the model's 80.1% -> 85.0%. GPT gained more, as expected. **The corrected figures remain a
floor**: there will be further false negatives not yet found.

**5.2 One comparison bug was fixed rather than adjudicated.** A manufacturer
against one of its instruments (`Illumina` against `NextSeq 500`) was scoring as
a contradiction rather than a difference of specificity; token containment could
not see it because "Illumina" is not a word in "NextSeq 500". Reclassified 10
conflicts.

**5.3 Known unfixed limitations of the grounding and comparison checks.**

* A bare publisher or PubMed URL carries neither author surname nor parseable
  year, so the citation matcher cannot tell that it names the same work as a
  prose citation. Three such conflicts were adjudicated by hand. Resolving
  identifiers to metadata would need network access and was not attempted.
* Vendor-specific shorthand is not expanded -- `GEM` for 10x gel bead-in-emulsion,
  `l-cys` for L-cysteine. The acronym table covers common domain terms only; the
  tail is long and was not pursued.
* Nominalisation is not matched: a manifest saying `excision` does not match a
  paper saying `excised`. Plurals and simple verb endings are handled;
  derivational morphology is not.
* PDF text extraction is unreliable at token level, and every failure found so
  far penalises the more detailed value. Five distinct causes are confirmed:
  line-break hyphenation (`cy-cles`), acronyms against expansions, compact
  temperature notation (`22c`, `28-30c`), comma thousands separators (`7,000`
  parsed as 7), and trademark glyphs fusing words (`FACSAria(TM)III` rendering as
  `facsariatmiii`). Two were fixed in code; the rest are open. **Grounding should
  therefore be read as a lower bound on both manifests**, and the gap between
  them as narrower than the figures suggest, since the model paraphrases and so
  produces longer values with more surface to misparse.
* The grounding band depends partly on value length. A long value absorbs a few
  unmatched terms and still scores `grounded`; a short value with the same
  proportion of unmatched terms drops to `partial` or `unsupported`. Short values
  made only of common domain words (`Plant incubator`) are not assessable at all.

**5.4 Referential integrity is deliberately not checked.** These manifests are
unvalidated extractions; a dangling foreign key is a spreadsheet defect, not a
misreading. The `file` sheet is excluded for a related reason: neither annotator
recorded real raw-file entries.

**5.5 Row matching is content-based and order-independent**, using optimal
assignment with propagation along the entity graph. State this: a positional or
identifier-based comparison of these manifests would report near-total
disagreement between documents that largely agree.

**5.6 All thresholds and weights are recorded in `out/run.json`** alongside input
SHA-256s, so any cut-off can be inspected rather than inferred.

---

## 6. Suggested framing

The useful conclusion is not a single accuracy score. It is a division of
labour: **GPT is a strong first-pass populator and a weak enumerator.** The row
skeleton -- how many samples, libraries and runs -- is better established by a
human or by a script reading the SRA/GEO record; GPT is then good at filling it.

The framing to avoid is "the model is N% accurate". The evidence does not support
it: the reference is unvalidated and wrong in roughly one conflict in seven
(1.4), a quarter of comparisons are unscoreable by construction (2.2), and there
is no human-versus-human baseline to say whether the remaining differences are
model-specific at all (2.9). What the evidence does support is a description of
*how* the two annotators differ -- in enumeration, in diligence per field, and in
the use of expert inference versus textual fidelity -- and a recommendation about
how to combine them.
