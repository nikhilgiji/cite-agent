Build a production-grade “Citation Agent” for LaTex research projects.

Goal:
Create a tool that analyzes a LaTeX project with multiple .tex files, a folder of literature PDFs, one or more .bib files, and optional web metadata lookup, then inserts highly accurate citations into the LaTex source in IEEE style. The system must prioritize correctness over coverage and must never invent citations.

Core product requirements:
1. Input:
   - A LaTeX project root directory
   - Potentially many .tex files connected via \input{}, \include{}, subfiles, or custom structure
   - One or more .bib files
   - A folder of literature PDFs
   - Optional DOI / URL / website metadata lookup for missing bibliography details
2. Output:
   - Updated .tex files with inserted citation commands
   - Updated .bib file with repaired or added entries when needed
   - A machine-readable audit report (JSON)
   - A human-readable review report (Markdown or HTML)
   - A dry-run diff mode before applying edits
3. Citation behavior:
   - Use existing BibTeX keys when available
   - If a suitable source exists only as a PDF, extract metadata and create a .bib entry
   - If metadata is incomplete, enrich from DOI / publisher / Crossref-like metadata services
   - Insert citations conservatively
   - Never cite a source unless supporting evidence is found in the source text or trusted metadata
   - Never hallucinate titles, authors, venues, years, DOIs, or BibTeX keys
4. IEEE requirement:
   - The system should support LaTeX projects using IEEE bibliography workflows
   - Detect whether the project uses BibTeX + IEEEtran or biblatex with IEEE-like style
   - Preserve the project’s existing citation command conventions where possible
   - Do not hand-format references in prose; maintain/refine .bib data and let LaTeX/BibTeX format output

Accuracy and safety constraints:
- Accuracy is the top priority.
- Favor “needs review” over risky auto-insertion.
- No fabricated citations.
- No unsupported claim-to-source matches.
- No replacing existing citations unless the replacement is demonstrably better and the user explicitly enables replacement mode.
- Every inserted citation must have an evidence trail in the audit report.
- Every recommendation must include a confidence score and evidence span(s).

System architecture to implement:
A. Project analysis
- Detect the main LaTeX file
- Build a dependency graph of .tex files from \input{}, \include{}, and related commands
- Detect bibliography declarations such as \bibliography{}, \addbibresource{}, and related patterns
- Detect citation commands in use, such as \cite{}, \citep{}, \citet{}, \parencite{}, etc.
- Detect whether the document appears to be IEEE-oriented

B. TeX parsing
- Parse LaTeX robustly enough to:
  - preserve section hierarchy
  - ignore comments
  - identify paragraphs and sentences
  - detect figures, tables, captions, equations, theorem-like environments
  - detect existing citation spans
- Extract “claim candidates” from prose
- Track source location for each claim candidate:
  - file path
  - section/subsection
  - paragraph index
  - sentence index
  - surrounding context

C. Claim classification
For each sentence/span classify:
- no citation needed
- background factual claim
- related work claim
- method attribution claim
- benchmark / result claim
- dataset / software / standard claim
- historical claim
- definitional claim
Also estimate:
- whether a citation already exists nearby
- whether a single source or multiple sources may be needed
- whether the claim is too vague for safe auto-citation

D. Bibliography ingestion
- Parse .bib files into normalized internal records
- Validate fields
- Deduplicate entries
- Detect malformed or incomplete entries
- Build mapping between BibTeX keys and normalized metadata

E. PDF ingestion
- Extract text and metadata from PDFs
- Prefer structured extraction where possible
- For each PDF store:
  - title
  - authors
  - abstract if available
  - section headings
  - chunked body text
  - references section if extractable
  - DOI / identifiers if found
  - file path and checksum
- Build search indexes over PDF chunks and metadata

F. Retrieval layer
Implement hybrid retrieval over:
- bib metadata
- PDF metadata
- PDF text chunks
Use:
- lexical retrieval (BM25 or equivalent)
- semantic embeddings retrieval
- rank fusion or weighted hybrid ranking
For each claim, retrieve top candidate sources and top candidate evidence spans

G. Verification layer
For each claim/source candidate pair:
- decide whether the source truly supports the claim
- classify support as:
  - direct support
  - partial support
  - indirect/weak support
  - contradiction
  - irrelevant
- extract evidence snippets and offsets
- score confidence
- reject citation if support is insufficient

H. Citation decision layer
For each claim:
- choose best source(s)
- map to existing BibTeX key if available
- otherwise generate a new .bib entry candidate
- decide exact insertion point in LaTeX
- avoid over-citation
- support grouped citations when justified
- flag ambiguous cases for review instead of editing

I. Editing layer
- Modify .tex files safely
- Preserve formatting as much as practical
- Avoid damaging LaTeX syntax
- Support dry-run diff mode
- Support apply mode
- Create backups or git-friendly patch output

J. Reporting layer
Produce:
1. JSON audit report with:
   - claim id
   - file path
   - original sentence
   - classification
   - retrieved candidates
   - chosen source(s)
   - evidence spans
   - confidence
   - action taken (inserted / skipped / flagged)
2. Human-readable Markdown report summarizing:
   - files analyzed
   - citations inserted
   - items needing review
   - bibliography fixes
   - compile or parsing errors

K. Validation layer
- Run basic LaTeX-aware sanity checks after edits
- Check for broken citation keys
- Check for malformed inserted commands
- Check for duplicate added .bib entries
- Optionally compile in a validation step if the environment supports it

Implementation details:
- Use Python
- Use a modular package structure
- Include CLI entry points
- Include tests
- Use typed code where practical
- Use Pydantic/dataclasses for schemas
- Use logging
- Add clear configuration via YAML or TOML
- Make components swappable (parser, retriever, PDF extractor, verifier)

Suggested repository structure:
citation_agent/
  pyproject.toml
  README.md
  src/citation_agent/
    __init__.py
    cli.py
    config.py
    models/
      schemas.py
    ingest/
      tex_project.py
      bib_loader.py
      pdf_loader.py
      metadata_lookup.py
    parse/
      tex_graph.py
      tex_extract.py
      sentence_split.py
      claim_detection.py
    retrieve/
      bm25.py
      embeddings.py
      hybrid.py
    verify/
      support_classifier.py
      evidence_selector.py
    decide/
      citation_decider.py
    edit/
      tex_rewriter.py
      bib_writer.py
      diff_writer.py
    report/
      audit_json.py
      markdown_report.py
    validate/
      sanity_checks.py
      compile_check.py
  tests/
  examples/

CLI to build:
- citation-agent scan --project /path/to/project --pdfs /path/to/pdfs --bib refs.bib
- citation-agent audit --project ... --out audit.json
- citation-agent apply --project ... --pdfs ... --bib ... --dry-run
- citation-agent apply --project ... --pdfs ... --bib ... --write
- citation-agent repair-bib --bib refs.bib --pdfs /path/to/pdfs

Important behavior rules:
- Do not hardcode one LaTeX template.
- Handle multiple .tex files.
- Respect existing citation commands if already in use.
- Preserve user edits and formatting.
- Do not add citations to every sentence blindly.
- Do not cite based only on title similarity.
- Require evidence.
- If confidence is below threshold, mark “needs_review” and do not insert.

Heuristics to implement:
- Related work sections are more citation-dense.
- Claims containing years, benchmarks, “widely used”, “state-of-the-art”, “proposed by”, “introduced in”, “according to”, or numerical comparisons usually need citations.
- Sentences already covered by nearby citations may not need another.
- First mention of a dataset, model, library, theorem, or standard often needs citation.
- Claims about the author’s own contribution often do not need external citation unless they compare to prior work.

Design the agent for two modes:
1. Audit mode:
   - no source edits
   - produce recommendations only
2. Apply mode:
   - write approved edits
   - generate diffs and reports

Now implement:
1. A full architecture skeleton
2. The core data models
3. The LaTeX project graph builder
4. .bib parser/normalizer
5. PDF text ingestion pipeline
6. Claim extraction pipeline
7. Retrieval pipeline
8. Verification pipeline
9. Citation insertion logic
10. JSON + Markdown reporting
11. CLI
12. Tests
13. Example config
14. README with usage examples

Engineering expectations:
- Build iteratively but end with runnable code
- Stub external integrations cleanly if needed, but keep interfaces real
- Where functionality is incomplete, leave clear TODOs and safe fallbacks
- Include docstrings and comments
- Prefer maintainable code over clever code
- Ensure the first version is usable in audit mode even if some advanced pieces remain basic

When making choices:
- choose the most conservative, reliability-oriented approach
- optimize for correctness, traceability, and debuggability
- expose confidence thresholds in config
- keep all evidence linked to source files and text spans

At the end:
- summarize what was built
- list remaining limitations
- show example CLI commands
- show the most important files created