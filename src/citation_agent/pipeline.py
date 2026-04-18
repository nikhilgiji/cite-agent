from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from citation_agent.config import CitationAgentConfig
from citation_agent.decide.citation_decider import decide_citation
from citation_agent.ingest.bib_loader import load_bib_entries
from citation_agent.ingest.metadata_lookup import enrich_pdf_metadata
from citation_agent.ingest.pdf_loader import load_pdfs
from citation_agent.ingest.tex_project import analyze_project
from citation_agent.models.schemas import AuditEntry, BibEntry, ExistingCitationResult, PipelineArtifacts
from citation_agent.parse.tex_extract import extract_claims, extract_existing_citation_checks
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
    bib_entry_map = {entry.key: entry for entry in bib_entries}
    pdf_documents = [enrich_pdf_metadata(document) for document in load_pdfs(pdf_dir)]

    claims = []
    existing_checks = []
    for tex_file in analysis.tex_files:
        claims.extend(extract_claims(Path(tex_file), Path(project_root)))
        existing_checks.extend(extract_existing_citation_checks(Path(tex_file)))

    decisions = []
    audit_entries = []
    existing_keys = {entry.key for entry in bib_entries}
    bib_target_path = bib_paths[0] if bib_paths else None
    existing_citation_results = verify_existing_citations(existing_checks, bib_entry_map, config)
    removable_statuses = {"missing_key", "unsupported"}
    blocking_by_file_and_offset: dict[tuple[str, int], bool] = {}
    for result in existing_citation_results:
        key = (result.file_path, result.start_offset)
        prior = blocking_by_file_and_offset.get(key, False)
        blocking_by_file_and_offset[key] = prior or result.status not in removable_statuses

    for claim in claims:
        candidates = retrieve_candidates(claim, bib_entries, pdf_documents, config.retrieval)
        verified = [verify_candidate(claim, candidate, config.verification) for candidate in candidates]
        verified.sort(key=lambda item: item.confidence, reverse=True)
        treat_existing_citation_as_blocking = blocking_by_file_and_offset.get(
            (claim.location.file_path, claim.location.start_offset),
            claim.has_nearby_citation,
        )
        decision = decide_citation(
            claim=claim,
            verified_candidates=verified,
            existing_keys=existing_keys,
            citation_commands=analysis.citation_commands,
            bib_target_path=bib_target_path,
            config=config,
            treat_existing_citation_as_blocking=treat_existing_citation_as_blocking,
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
        existing_citation_results=existing_citation_results,
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
        "existing_citation_checks": len(artifacts.existing_citation_results),
        "ieee_like": artifacts.analysis.ieee_like,
    }


def verify_existing_citations(existing_checks, bib_entry_map, config: CitationAgentConfig) -> list[ExistingCitationResult]:
    results: list[ExistingCitationResult] = []
    for check in existing_checks:
        missing_keys = [key for key in check.cited_keys if key not in bib_entry_map]
        if missing_keys:
            results.append(
                ExistingCitationResult(
                    check_id=check.check_id,
                    file_path=check.location.file_path,
                    line_number=check.location.line_number,
                    start_offset=check.location.start_offset,
                    end_offset=check.location.end_offset,
                    sentence_text=check.sentence_text,
                    citation_command=check.citation_command,
                    cited_keys=check.cited_keys,
                    status="missing_key",
                    confidence=0.0,
                    reason="One or more cited BibTeX keys were not found in the loaded bibliography.",
                    missing_keys=missing_keys,
                )
            )
            continue

        verified_candidates = []
        for key in check.cited_keys:
            entry = bib_entry_map[key]
            title = entry.title or key
            evidence_spans = [span for span in [entry.title, entry.author, entry.fields.get("abstract", "")] if span]
            lexical_candidate = retrieve_candidates(
                claim=type("ClaimProxy", (), {"text": check.cleaned_claim_text})(),
                bib_entries=[entry],
                pdf_documents=[],
                config=config.retrieval,
            )
            if not lexical_candidate:
                continue
            verified_candidates.append(
                verify_candidate(
                    type("ClaimProxy", (), {"text": check.cleaned_claim_text})(),
                    lexical_candidate[0],
                    config.verification,
                )
            )

        if not verified_candidates:
            results.append(
                ExistingCitationResult(
                    check_id=check.check_id,
                    file_path=check.location.file_path,
                    line_number=check.location.line_number,
                    start_offset=check.location.start_offset,
                    end_offset=check.location.end_offset,
                    sentence_text=check.sentence_text,
                    citation_command=check.citation_command,
                    cited_keys=check.cited_keys,
                    status="unsupported",
                    confidence=0.0,
                    reason="Could not derive supporting evidence from the cited bibliography entries.",
                )
            )
            continue

        verified_candidates.sort(key=lambda item: item.confidence, reverse=True)
        best = verified_candidates[0]
        if best.support_label == "direct_support":
            status = "supported"
            reason = "The cited source plausibly supports the local sentence."
        elif best.support_label == "partial_support" and best.confidence >= config.verification.auto_insert_threshold:
            status = "supported"
            reason = "The cited source appears consistent with the local sentence under the current confidence threshold."
        elif best.support_label == "partial_support":
            status = "weak_support"
            reason = "The cited source is related, but support looks partial and should be reviewed."
        else:
            status = "unsupported"
            reason = "The cited source does not appear to support the local sentence strongly enough."

        results.append(
            ExistingCitationResult(
                check_id=check.check_id,
                file_path=check.location.file_path,
                line_number=check.location.line_number,
                start_offset=check.location.start_offset,
                end_offset=check.location.end_offset,
                sentence_text=check.sentence_text,
                citation_command=check.citation_command,
                cited_keys=check.cited_keys,
                status=status,
                confidence=best.confidence,
                reason=reason,
                evidence_spans=best.evidence_spans,
            )
        )
    return results
