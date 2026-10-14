# V5.2 final delivery inventory

- Primary complete source: `CommonPose_EMBC2027_V5_2_EN.tex` (all prose, equations, Table I, and ten references inline).
- Segmented editable equivalents: `main.tex`, `manuscript.tex`, `table1.tex`, `references.bib`.
- English build entry: `build.ps1` compiles the complete English source.
- Final vector/color/grayscale/editable assets: three figures, six PDF files, six SVG files, six PNG files.
- Frozen plotting inputs and parameters: `reproducibility/`; original hashes in `review/FIGURE_SOURCE_HASHES.json`.
- English and Chinese five-page PDFs: `output/pdf/`.
- Exact V5.1-to-V5.2 source and figure-generator changes: `review/V5_1_TO_V5_2.diff`.
- Author confirmation, direct paired contrast, 39 bilingual paragraphs, frozen-data checks, template/reference checks, final compile logs, visual QA, Go/No-Go and GitHub receipts: `review/`.
- Page render previews and extracted text: `qa/`.
- Readme, Chinese change log, and successor handover: project root.

The source archive includes all dependencies needed to compile the English manuscript. It does not distribute the local Chinese font, Python runtime, original signals, trained weights, or credentials. Chinese is delivered as a complete review PDF with paragraph mapping, not as a portable Chinese font installation. The verification script is a repository audit and also checks the preserved V5.1 lane; compilation of the English manuscript needs only the packaged project and a LaTeX engine.
