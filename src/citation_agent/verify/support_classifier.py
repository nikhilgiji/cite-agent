from __future__ import annotations

from citation_agent.config import VerificationConfig
from citation_agent.models.schemas import ClaimCandidate, RetrievedCandidate, VerifiedCandidate
from citation_agent.retrieve.bm25 import lexical_overlap_score
from citation_agent.retrieve.embeddings import semantic_similarity
from citation_agent.verify.evidence_selector import select_evidence


def verify_candidate(
    claim: ClaimCandidate,
    candidate: RetrievedCandidate,
    config: VerificationConfig,
) -> VerifiedCandidate:
    joined_evidence = " ".join(candidate.evidence_spans) or candidate.title
    lexical = lexical_overlap_score(claim.text, joined_evidence)
    semantic = semantic_similarity(claim.text, joined_evidence)
    confidence = (candidate.score * 0.4) + (lexical * 0.35) + (semantic * 0.25)
    evidence_spans = select_evidence(claim, candidate)

    if confidence >= config.direct_support_threshold:
        support_label = "direct_support"
    elif confidence >= config.partial_support_threshold:
        support_label = "partial_support"
    elif confidence > 0.2:
        support_label = "indirect_weak_support"
    else:
        support_label = "irrelevant"

    return VerifiedCandidate(
        candidate=candidate,
        support_label=support_label,
        confidence=confidence,
        evidence_spans=evidence_spans,
        contradicted=False,
    )
