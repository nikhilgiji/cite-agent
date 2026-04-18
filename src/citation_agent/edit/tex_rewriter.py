from __future__ import annotations

from pathlib import Path

from citation_agent.models.schemas import CitationDecision, ClaimCandidate


def _citation_text(decision: CitationDecision) -> str:
    command = decision.citation_command or "cite"
    keys = ",".join(decision.bib_keys)
    return f" \\{command}{{{keys}}}"


def apply_citation_decisions(
    tex_path: str | Path,
    claims: list[ClaimCandidate],
    decisions: list[CitationDecision],
) -> tuple[str, int]:
    path = Path(tex_path)
    text = path.read_text(encoding="utf-8", errors="ignore")
    decisions_by_claim = {
        decision.claim_id: decision
        for decision in decisions
        if decision.action == "inserted" and decision.bib_keys
    }
    file_claims = [claim for claim in claims if claim.location.file_path == str(path.resolve())]
    file_claims.sort(key=lambda item: item.location.start_offset, reverse=True)

    inserted = 0
    for claim in file_claims:
        decision = decisions_by_claim.get(claim.claim_id)
        if not decision:
            continue
        start = claim.location.start_offset
        end = claim.location.end_offset
        original = text[start:end]
        citation = _citation_text(decision)
        if citation.strip() in original:
            continue
        replacement = f"{original}{citation}"
        text = text[:start] + replacement + text[end:]
        inserted += 1

    return text, inserted
