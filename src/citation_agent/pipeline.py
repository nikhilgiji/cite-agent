from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from citation_agent.config import CitationAgentConfig
from citation_agent.decide.citation_decider import decide_citation
from citation_agent.ingest.bib_loader import load_bib_entries
from citation_agent.ingest.metadata_lookup import enrich_pdf_metadata
from citation_agent.ingest.pdf_loader import load_pdfs
from citation_agent.ingest.tex_project import analyze_project
from citation_agent.models.schemas import AuditEntry, BibEntry, PipelineArtifacts
from citation_agent.parse.tex_extract import extract_claims
from citation_agent.report.markdown_report import render_markdown_report
from citation_agent.retrieve.hybrid import retrieve_candidates
from citation_agent.validate.sanity_checks import run_sanity_checks
from citation_agent.verify.support_classifier import verify_candidate


def run_pipeline(
    project_root: str | Path,
    pdf_dir: str | Path | None,
    explicit_bib_paths: list[str] | None,
    config: CitationAgentConfig,
) -> PipelineArtifacts:
    analysis = analyze_project(project_root)
    bib_paths = explicit_bib_paths or analysis.bibliography_files
    bib_entries = load_bib_entries(bib_paths)
    pdf_documents = [enrich_pdf_metadata(document) for document in load_pdfs(pdf_dir)]

    claims = []
    for tex_file in analysis.tex_files:
        claims.extend(extract_claims(Path(tex_file), Path(project_root)))

    decisions = []
    audit_entries = []
    existing_keys = {entry.key for entry in bib_entries}
    bib_target_path = bib_paths[0] if bib_paths else None

    for claim in claims:
        candidates = retrieve_candidates(claim, bib_entries, pdf_documents, config.retrieval)
        verified = [verify_candidate(claim, candidate, config.verification) for candidate in candidates]
        verified.sort(key=lambda item: item.confidence, reverse=True)
        decision = decide_citation(
            claim=claim,
            verified_candidates=verified,
            existing_keys=existing_keys,
            citation_commands=analysis.citation_commands,
            bib_target_path=bib_target_path,
            config=config,
        )
        decisions.append(decision)

        for entry in decision.new_bib_entries:
            existing_keys.add(entry.key)

        audit_entries.append(
            AuditEntry(
                claim_id=claim.claim_id,
                file_path=claim.location.file_path,
                original_sentence=claim.text,
                classification=claim.classification,
                retrieved_candidates=[
                    {
                        "source_type": item.candidate.source_type,
                        "source_id": item.candidate.source_id,
                        "title": item.candidate.title,
                        "score": round(item.candidate.score, 4),
                        "support_label": item.support_label,
                        "confidence": round(item.confidence, 4),
                    }
                    for item in verified
                ],
                chosen_sources=decision.bib_keys,
                evidence_spans=decision.evidence_spans,
                confidence=decision.confidence,
                action_taken=decision.action,
                reason=decision.reason,
            )
        )

    added_bib_entries: list[BibEntry] = []
    seen_added: set[str] = set()
    for decision in decisions:
        for entry in decision.new_bib_entries:
            if entry.key not in seen_added:
                seen_added.add(entry.key)
                added_bib_entries.append(entry)

    validation_messages = run_sanity_checks(decisions, bib_entries)

    artifacts = PipelineArtifacts(
        analysis=analysis,
        claims=claims,
        bib_entries=bib_entries,
        pdf_documents=pdf_documents,
        decisions=decisions,
        audit_entries=audit_entries,
        markdown_report="",
        added_bib_entries=added_bib_entries,
        validation_messages=validation_messages,
    )
    artifacts.markdown_report = render_markdown_report(artifacts)
    return artifacts


def summarize_scan(artifacts: PipelineArtifacts) -> dict[str, int | bool]:
    decision_counts: dict[str, int] = defaultdict(int)
    for decision in artifacts.decisions:
        decision_counts[decision.action] += 1
    return {
        "tex_files": len(artifacts.analysis.tex_files),
        "bib_files": len(artifacts.analysis.bibliography_files),
        "pdfs": len(artifacts.pdf_documents),
        "claims": len(artifacts.claims),
        "inserted": decision_counts.get("inserted", 0),
        "needs_review": decision_counts.get("needs_review", 0),
        "ieee_like": artifacts.analysis.ieee_like,
    }
