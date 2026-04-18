from __future__ import annotations

from pathlib import Path
import re

from citation_agent.config import CitationAgentConfig
from citation_agent.models.schemas import BibEntry, CitationDecision, ClaimCandidate, VerifiedCandidate


NON_ALNUM_PATTERN = re.compile(r"[^A-Za-z0-9]+")


def preferred_citation_command(commands: list[str]) -> str:
    for candidate in ("cite", "citep", "parencite", "autocite", "citet"):
        if candidate in commands:
            return candidate
    return commands[0] if commands else "cite"


def make_bib_key_from_pdf_title(title: str) -> str:
    normalized = NON_ALNUM_PATTERN.sub("", title.title())
    return normalized[:32] or "GeneratedSource"


def candidate_to_bib_entry(candidate: VerifiedCandidate, bib_path: str) -> BibEntry | None:
    if candidate.candidate.source_type != "pdf":
        return None
    doi = candidate.candidate.metadata.get("doi", "").strip()
    if not doi:
        return None
    title = candidate.candidate.title.strip()
    key = make_bib_key_from_pdf_title(title)
    return BibEntry(
        entry_type="misc",
        key=key,
        fields={
            "title": title,
            "doi": doi,
            "howpublished": "{Local PDF metadata import}",
        },
        source_path=bib_path,
        malformed=False,
    )


def decide_citation(
    claim: ClaimCandidate,
    verified_candidates: list[VerifiedCandidate],
    existing_keys: set[str],
    citation_commands: list[str],
    bib_target_path: str | None,
    config: CitationAgentConfig,
    treat_existing_citation_as_blocking: bool = True,
) -> CitationDecision:
    if not claim.needs_citation:
        return CitationDecision(
            claim_id=claim.claim_id,
            action="skipped",
            citation_command=None,
            reason="Heuristics did not mark this sentence as requiring a citation.",
        )

    if claim.has_nearby_citation and treat_existing_citation_as_blocking and not config.editing.replacement_mode:
        return CitationDecision(
            claim_id=claim.claim_id,
            action="skipped",
            citation_command=None,
            reason="Existing citation found nearby and replacement mode is disabled.",
        )

    if claim.vague:
        return CitationDecision(
            claim_id=claim.claim_id,
            action="needs_review",
            citation_command=None,
            reason="Claim is too vague for safe automatic citation.",
        )

    if not verified_candidates:
        return CitationDecision(
            claim_id=claim.claim_id,
            action="needs_review",
            citation_command=None,
            reason="No supporting sources were retrieved.",
        )

    best = verified_candidates[0]
    if best.support_label not in {"direct_support", "partial_support"}:
        return CitationDecision(
            claim_id=claim.claim_id,
            action="needs_review",
            citation_command=None,
            confidence=best.confidence,
            reason="Retrieved sources did not provide sufficient support.",
            evidence_spans=best.evidence_spans,
        )

    if best.candidate.source_type == "bib":
        if best.confidence < config.verification.auto_insert_threshold:
            return CitationDecision(
                claim_id=claim.claim_id,
                action="needs_review",
                citation_command=None,
                bib_keys=[best.candidate.source_id],
                confidence=best.confidence,
                reason="Support exists but confidence is below auto-insert threshold.",
                evidence_spans=best.evidence_spans,
            )
        return CitationDecision(
            claim_id=claim.claim_id,
            action="inserted",
            citation_command=preferred_citation_command(citation_commands),
            bib_keys=[best.candidate.source_id],
            confidence=best.confidence,
            reason="Existing bibliography entry directly supports the claim.",
            evidence_spans=best.evidence_spans,
        )

    if best.candidate.source_type == "pdf" and bib_target_path:
        new_entry = candidate_to_bib_entry(best, bib_target_path)
        if new_entry and new_entry.key not in existing_keys and best.confidence >= 0.9:
            return CitationDecision(
                claim_id=claim.claim_id,
                action="inserted",
                citation_command=preferred_citation_command(citation_commands),
                bib_keys=[new_entry.key],
                confidence=best.confidence,
                reason="Local PDF has strong metadata and support; generated bibliography entry.",
                evidence_spans=best.evidence_spans,
                new_bib_entries=[new_entry],
            )

    return CitationDecision(
        claim_id=claim.claim_id,
        action="needs_review",
        citation_command=None,
        confidence=best.confidence,
        reason="Candidate support was not strong enough for automatic insertion.",
        evidence_spans=best.evidence_spans,
    )
