from __future__ import annotations

from pathlib import Path
import re

from citation_agent.models.schemas import CitationDecision, ClaimCandidate, ExistingCitationResult


def _citation_text(decision: CitationDecision) -> str:
    command = decision.citation_command or "cite"
    keys = ",".join(decision.bib_keys)
    return f" \\{command}{{{keys}}}"


def _remove_citations_from_segment(segment: str, removable_results: list[ExistingCitationResult]) -> tuple[str, int]:
    removed = 0
    for result in removable_results:
        keys_pattern = r"\s*,\s*".join(re.escape(key) for key in result.cited_keys)
        pattern = re.compile(rf"\s*\\{re.escape(result.citation_command)}\{{{keys_pattern}\}}")
        updated_segment, count = pattern.subn("", segment, count=1)
        if count <= 0:
            continue
        segment = updated_segment
        removed += count

    segment = re.sub(r"\s+([.,;:])", r"\1", segment)
    segment = re.sub(r"\s{2,}", " ", segment)
    return segment, removed


def apply_citation_decisions(
    tex_path: str | Path,
    claims: list[ClaimCandidate],
    decisions: list[CitationDecision],
    existing_citation_results: list[ExistingCitationResult] | None = None,
) -> tuple[str, int, int]:
    path = Path(tex_path)
    text = path.read_text(encoding="utf-8", errors="ignore")
    decisions_by_claim = {
        decision.claim_id: decision
        for decision in decisions
        if decision.action == "inserted" and decision.bib_keys
    }
    file_claims = [claim for claim in claims if claim.location.file_path == str(path.resolve())]
    file_claims.sort(key=lambda item: item.location.start_offset, reverse=True)
    removable_results = [
        result
        for result in (existing_citation_results or [])
        if result.file_path == str(path.resolve()) and result.status in {"missing_key", "unsupported"}
    ]
    removable_by_start: dict[int, list[ExistingCitationResult]] = {}
    for result in removable_results:
        removable_by_start.setdefault(result.start_offset, []).append(result)

    inserted = 0
    removed = 0
    handled_starts: set[int] = set()
    for claim in file_claims:
        start = claim.location.start_offset
        end = claim.location.end_offset
        segment = text[start:end]
        sentence_removals = removable_by_start.get(start, [])
        if sentence_removals:
            segment, removed_count = _remove_citations_from_segment(segment, sentence_removals)
            removed += removed_count
            handled_starts.add(start)

        decision = decisions_by_claim.get(claim.claim_id)
        replacement = segment
        if decision:
            citation = _citation_text(decision)
            if citation.strip() not in segment:
                replacement = f"{segment}{citation}"
                inserted += 1
        text = text[:start] + replacement + text[end:]

    unhandled_results = [result for result in removable_results if result.start_offset not in handled_starts]
    unhandled_results.sort(key=lambda item: item.start_offset, reverse=True)
    for result in unhandled_results:
        start = result.start_offset
        end = result.end_offset
        segment = text[start:end]
        updated_segment, removed_count = _remove_citations_from_segment(segment, [result])
        if removed_count <= 0:
            continue
        text = text[:start] + updated_segment + text[end:]
        removed += removed_count

    return text, inserted, removed
