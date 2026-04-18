from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SourceLocation:
    file_path: str
    line_number: int
    section: str | None
    paragraph_index: int
    sentence_index: int
    start_offset: int
    end_offset: int
    context: str


@dataclass(slots=True)
class ClaimCandidate:
    claim_id: str
    text: str
    classification: str
    needs_citation: bool
    has_nearby_citation: bool
    multi_source_hint: bool
    vague: bool
    location: SourceLocation


@dataclass(slots=True)
class ExistingCitationCheck:
    check_id: str
    citation_command: str
    cited_keys: list[str]
    sentence_text: str
    cleaned_claim_text: str
    location: SourceLocation


@dataclass(slots=True)
class BibEntry:
    entry_type: str
    key: str
    fields: dict[str, str]
    source_path: str
    malformed: bool = False

    @property
    def title(self) -> str:
        return self.fields.get("title", "")

    @property
    def author(self) -> str:
        return self.fields.get("author", "")

    @property
    def year(self) -> str:
        return self.fields.get("year", "")


@dataclass(slots=True)
class PDFDocument:
    path: str
    checksum: str
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    abstract: str | None = None
    section_headings: list[str] = field(default_factory=list)
    chunks: list[str] = field(default_factory=list)
    references_text: str | None = None
    doi: str | None = None
    url: str | None = None


@dataclass(slots=True)
class RetrievedCandidate:
    source_type: str
    source_id: str
    title: str
    score: float
    evidence_spans: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class VerifiedCandidate:
    candidate: RetrievedCandidate
    support_label: str
    confidence: float
    evidence_spans: list[str]
    contradicted: bool = False


@dataclass(slots=True)
class CitationDecision:
    claim_id: str
    action: str
    citation_command: str | None
    bib_keys: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reason: str = ""
    evidence_spans: list[str] = field(default_factory=list)
    new_bib_entries: list[BibEntry] = field(default_factory=list)


@dataclass(slots=True)
class AuditEntry:
    claim_id: str
    file_path: str
    original_sentence: str
    classification: str
    retrieved_candidates: list[dict[str, Any]]
    chosen_sources: list[str]
    evidence_spans: list[str]
    confidence: float
    action_taken: str
    reason: str


@dataclass(slots=True)
class ExistingCitationResult:
    check_id: str
    file_path: str
    line_number: int
    sentence_text: str
    citation_command: str
    cited_keys: list[str]
    status: str
    confidence: float
    reason: str
    evidence_spans: list[str] = field(default_factory=list)
    missing_keys: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProjectAnalysis:
    project_root: str
    tex_files: list[str]
    main_tex: str | None
    dependency_graph: dict[str, list[str]]
    bibliography_files: list[str]
    bibliography_declarations: list[str]
    citation_commands: list[str]
    ieee_like: bool


@dataclass(slots=True)
class PipelineArtifacts:
    analysis: ProjectAnalysis
    claims: list[ClaimCandidate]
    bib_entries: list[BibEntry]
    pdf_documents: list[PDFDocument]
    decisions: list[CitationDecision]
    audit_entries: list[AuditEntry]
    existing_citation_results: list[ExistingCitationResult]
    markdown_report: str
    applied_files: dict[str, str] = field(default_factory=dict)
    added_bib_entries: list[BibEntry] = field(default_factory=list)
    validation_messages: list[str] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def project_relative(path: str | Path, root: str | Path) -> str:
    path_obj = Path(path)
    root_obj = Path(root)
    try:
        return str(path_obj.relative_to(root_obj))
    except ValueError:
        return str(path_obj)
