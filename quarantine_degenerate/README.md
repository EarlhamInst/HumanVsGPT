# Quarantined manifest pairs

Five pairs held back from the main comparison because the **human** manifest
contains blocks of rows that are indistinguishable from one another: identical in
every descriptive field *and* in the parent they hang from, differing only by an
auto-incremented surrogate ID. That is the signature of a spreadsheet fill-down,
not of that many real entities.

They are quarantined rather than deleted because the defect is in the reference
side. Scored as-is they would penalise the GPT manifest for failing to reproduce
rows that do not describe anything — `pca_manifest_marchant_2025.xlsx` declares
2182 maize anther samples, all reading `Zea mays / anther / W23 bz2 /
Standford, CA, USA`, against GPT's 11.

## Criterion

A pair is quarantined when any sheet in the human manifest has

    redundant rows >= 10  AND  redundant rows / total rows >= 0.90

where redundancy is measured by `align.content_signature`, which treats a row's
own primary key as arbitrary but its foreign keys as part of its identity. Eight
cell suspensions sharing identical protocol text are eight distinct suspensions
if they point at eight distinct samples; only rows alike in both content and
parentage count as redundant.

See `quarantine_reasons.csv` for the sheet and counts that triggered each.

## Borderline pairs left in the main set

These show milder redundancy, consistent with the human simply not recording a
distinguishing field rather than with a fill-down, and remain in the comparison:

| pair | sheet | rows -> distinct | ratio |
|---|---|---|---|
| guillotin_2023 | sample | 22 -> 4 | 82% |
| vukasinovic_2025 | sample | 13 -> 2 | 85% |
| Sun_2025 | sample | 8 -> 2 | 75% |
| cao_2023 | sample | 8 -> 4 | 50% |
| zong_2022 | sample | 5 -> 3 | 40% |

Cao is the instructive case: its human sample sheet records genotype but never
records inoculation treatment, so the eight samples collapse to four described
states. The rows are real; the description is incomplete. The comparison reports
this as ambiguous alignment rather than as degeneracy.

## Restoring a pair

Move both files back and re-add the row to `comparason_matched/matched_pairs.csv`.
The full 26-pair list before quarantine is preserved here as
`matched_pairs_all26.csv`.
