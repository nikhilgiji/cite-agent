# Citation Agent

Citation Agent is a conservative, correctness-first tool for adding evidence-backed citations to LaTeX research projects.

It analyzes multi-file TeX projects, ingests existing BibTeX entries and local literature PDFs, detects citation-worthy claims, retrieves candidate sources, verifies support heuristically, and then produces safe edits plus detailed audit trails.

The guiding rule is simple: when support is weak or ambiguous, the tool should flag the sentence for review instead of inserting a risky citation.

## What It Does

- Scans LaTeX projects with multiple `.tex` files linked through `\input{}`, `\include{}`, or similar structures
- Detects bibliography declarations and citation command conventions already used in the project
- Parses `.bib` files into normalized internal records
- Ingests local PDFs and extracts lightweight metadata and text chunks
- Finds candidate claims that are likely to need citations
- Retrieves possible supporting sources from existing bibliography entries and local PDFs
- Verifies support conservatively before deciding whether to insert a citation or mark the claim for review
- Produces JSON audit output, Markdown reports, dry-run diffs, and optional file edits

## Design Goals

- Prioritize accuracy over coverage
- Never invent authors, titles, venues, years, DOIs, or BibTeX keys
- Prefer `needs_review` over unsafe auto-insertion
- Preserve existing LaTeX citation style and bibliography workflow where possible
- Keep the architecture modular so parser, retriever, verifier, and PDF extraction components can be upgraded independently

## Current Status

This repository already includes a working end-to-end foundation:

- project analysis
- TeX dependency detection
- claim extraction heuristics
- `.bib` ingestion
- lightweight PDF ingestion
- hybrid lexical/semantic-style retrieval
- verification and citation decision logic
- safe `.tex` rewriting
- `.bib` append support
- audit and Markdown reporting
- CLI commands and tests

Some subsystems are intentionally lightweight in this first version:

- PDF extraction is heuristic rather than production OCR-quality
- metadata enrichment over DOI/Crossref-style services is stubbed
- semantic retrieval is placeholder-grade, not embedding-backed yet
- compile validation is not yet wired to a real LaTeX toolchain

That means the project is usable today as a conservative local assistant, while still leaving room for stronger retrieval and verification layers.

## Repository Layout

```text
cite-agent/
├── PROJECT.md
├── README.md
├── pyproject.toml
├── src/
│   └── citation_agent/
│       ├── cli.py
│       ├── config.py
│       ├── pipeline.py
│       ├── decide/
│       ├── edit/
│       ├── ingest/
│       ├── models/
│       ├── parse/
│       ├── report/
│       ├── retrieve/
│       ├── validate/
│       └── verify/
└── tests/
```

## Requirements

- Python `3.11+`
- A LaTeX project containing one or more `.tex` files
- Optional `.bib` files
- Optional directory of PDFs

## Installation

### Local editable install

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

After installation, the CLI is available as:

```bash
citation-agent --help
```

If you do not want to install the package yet, you can run it directly from the repo:

```bash
PYTHONPATH=src python3 -m citation_agent.cli --help
```

## CLI Commands

### 1. Scan a project

Use `scan` to inspect a project and summarize what Citation Agent found.

```bash
citation-agent scan \
  --project /path/to/latex-project \
  --pdfs /path/to/pdfs \
  --bib /path/to/refs.bib
```

This reports a compact JSON summary including:

- number of TeX files
- number of bibliography files
- number of PDFs ingested
- number of detected claims
- number of auto-insertable citations
- number of items needing review
- whether the project appears IEEE-like

### 2. Generate an audit report

Use `audit` to run the pipeline and write a machine-readable report.

```bash
citation-agent audit \
  --project /path/to/latex-project \
  --pdfs /path/to/pdfs \
  --bib /path/to/refs.bib \
  --out audit.json
```

This also prints a Markdown summary to the terminal.

### 3. Generate a readable text review report

Use `review` when you want a human-readable plain text report that answers the core questions directly:

- which existing citations look valid
- which existing citations are weak but should be kept for review
- which citations look invalid or incorrect
- which claims are missing citations and can be added automatically
- which claims still need manual review
- which additional public citation suggestions may be relevant

```bash
citation-agent review \
  --project /path/to/latex-project \
  --pdfs /path/to/pdfs \
  --bib /path/to/refs.bib \
  --out citation-review-report.txt
```

The text report includes:

- TeX file path
- line number
- paragraph number
- sentence text
- action or status
- confidence
- short explanation

### 4. Preview edits with dry-run

Use `apply --dry-run` to see the proposed diffs without modifying files.

```bash
citation-agent apply \
  --project /path/to/latex-project \
  --pdfs /path/to/pdfs \
  --bib /path/to/refs.bib \
  --dry-run
```

You can also save a readable text summary of the planned changes:

```bash
citation-agent apply \
  --project /path/to/latex-project \
  --pdfs /path/to/pdfs \
  --bib /path/to/refs.bib \
  --dry-run \
  --report-out citation-apply-report.txt
```

### 5. Write edits to disk

Use `apply --write` to run the citation repair flow against the content:

- verify existing citations first
- remove clearly wrong citations such as missing keys or unsupported citations
- add missing supported citations where the evidence is strong enough
- append any approved new BibTeX entries

```bash
citation-agent apply \
  --project /path/to/latex-project \
  --pdfs /path/to/pdfs \
  --bib /path/to/refs.bib \
  --write
```

When writing edits, the tool creates backup files using the configured backup suffix.

### 6. Repair bibliography from local PDFs

Use `repair-bib` to append conservatively generated bibliography entries when strong enough metadata exists.

```bash
citation-agent repair-bib \
  --bib /path/to/refs.bib \
  --pdfs /path/to/pdfs
```

### 7. Verify citations that already exist

Use `verify-existing` to inspect citation commands already present in the TeX source and write a plain text report showing whether the cited BibTeX entries look supported, weak, unsupported, or missing.

```bash
citation-agent verify-existing \
  --project /path/to/latex-project \
  --pdfs /path/to/pdfs \
  --bib /path/to/refs.bib \
  --out existing-citation-report.txt
```

The report is intentionally easy to share and review in any editor. It includes:

- the file and sentence containing the citation
- the exact line number in the `.tex` file
- the citation command and cited keys
- a status such as `supported`, `weak_support`, `unsupported`, or `missing_key`
- a confidence score
- a short reason
- evidence snippets when available

### 8. Optional public database lookup

If you want additional citation suggestions beyond your local `.bib` files and PDFs, enable public lookup:

```bash
citation-agent --enable-public-lookup review \
  --project /path/to/latex-project \
  --pdfs /path/to/pdfs \
  --bib /path/to/refs.bib \
  --out citation-review-report.txt
```

The current implementation uses Crossref as an optional suggestion source. These public suggestions are reported as readable recommendations only. They are not treated as verified evidence automatically.

## Recommended Workflow

The safest way to use Citation Agent is:

1. Run `scan`
2. Run `review` to get a readable text report across the project
3. Run `verify-existing` if you want the dedicated existing-citation-only report
4. Run `apply --dry-run --report-out ...` to preview repairs to the content
5. Review which wrong citations would be removed and which missing citations would be added
6. Run `apply --write` only after checking the diff

This matches the tool’s design philosophy: audit first, edit second.

## Example

Run directly from the repository without installation:

```bash
PYTHONPATH=src python3 -m citation_agent.cli scan \
  --project ~/research/my-paper \
  --pdfs ~/research/library \
  --bib ~/research/my-paper/refs.bib
```

Generate an audit file:

```bash
PYTHONPATH=src python3 -m citation_agent.cli audit \
  --project ~/research/my-paper \
  --pdfs ~/research/library \
  --bib ~/research/my-paper/refs.bib \
  --out ./audit.json
```

Preview changes:

```bash
PYTHONPATH=src python3 -m citation_agent.cli apply \
  --project ~/research/my-paper \
  --pdfs ~/research/library \
  --bib ~/research/my-paper/refs.bib \
  --dry-run
```

In repair mode, the dry-run may show both kinds of content edits in the same pass:

- removal of clearly wrong citations already present in the sentence
- insertion of a supported replacement citation or a newly missing citation

## Configuration

Citation Agent supports loading configuration from TOML or JSON through `--config`.

Current configurable areas include:

- retrieval weights
- top-k retrieval depth
- verification thresholds
- editing behavior
- backup suffix

Example:

```bash
citation-agent --config ./config.toml scan --project /path/to/project
```

## Output Artifacts

The pipeline can produce:

- updated `.tex` content with inserted citation commands
- updated `.bib` content with appended entries where safe
- JSON audit data
- Markdown review summaries
- dry-run unified diffs
- validation warnings for missing keys or malformed inserted commands

## Safety Guarantees

Citation Agent is intentionally conservative. In the current implementation:

- it does not replace existing citations unless replacement mode is enabled
- it does not auto-insert when evidence is vague
- it does not generate bibliography metadata unless the available metadata is strong enough
- it keeps a reason and confidence score for every decision

If a claim cannot be supported confidently, the system should output `needs_review` rather than guessing.

## Development

### Run tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

### Verify the package imports

```bash
PYTHONPATH=src python3 -m compileall src
```

## Using It With Codex

If you are building with Codex in this repository, you can ask Codex to:

- run a scan on a target LaTeX project
- generate an audit report
- preview citation diffs
- improve specific subsystems such as PDF extraction, metadata enrichment, or retrieval
- add tests and harden safety rules

Example requests:

- `Run Citation Agent on this sample LaTeX project and summarize the output.`
- `Show me the dry-run diff before applying edits.`
- `Improve PDF metadata extraction and extend the tests.`

## Roadmap

Natural next improvements for this repo are:

- real PDF text extraction and OCR support
- Crossref or DOI-based metadata enrichment
- embedding-backed retrieval
- stronger claim classification
- better evidence alignment and contradiction detection
- LaTeX compile validation
- richer HTML reporting

## License

No license has been added yet. If you want other people to use, modify, and redistribute this project safely, add a license before publishing broadly.
