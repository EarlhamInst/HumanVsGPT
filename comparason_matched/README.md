# The manifest corpus

Twenty-one papers, each described twice: once by a human curator and once by
GPT, using the same eight-sheet PCA manifest template.

* `human/` -- manifests produced by human curators
* `gpt/` -- manifests produced by GPT from the same papers
* `matched_pairs.csv` -- which human file corresponds to which GPT file
* `paper_pdfs.csv` -- which source PDF each pair describes

## Provenance

Both sides were extracted from the published manuscripts (main text; no
supplementary material). The PDFs themselves are not distributed here. The
grounding analysis needs them, so reproducing that part requires obtaining the
21 papers named in `paper_pdfs.csv`.

These manifests are derived metadata, not the publications. See `../LICENSE`.

## How the pairs were established

Not by filename. The human directory uses two incompatible naming conventions
and several filenames carry the wrong year -- `pca_manifest_Feng_2025.xlsx` is
the 2022 paper, `pca_manifest_dorrity_2020.xlsx` the 2021 one. Pairing was done
on the study title and author list held *inside* each workbook, which is
content the annotators transcribed rather than metadata a filename asserts.

Of 30 human and 27 GPT manifests originally present:

* two papers had duplicate human manifests, one under each naming convention;
  the later revision of each was kept (Turco, Dorrity)
* two templates were excluded (`pca_manifest_template_empty.xlsx`, and a
  combined workbook holding ten studies in one set of sheets)
* three papers had no counterpart on the other side (Lee 2023, Satterlee 2020,
  Picard 2021)
* five pairs were quarantined -- see `../quarantine_degenerate/README.md`
