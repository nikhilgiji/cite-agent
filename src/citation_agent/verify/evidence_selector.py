from __future__ import annotations

from citation_agent.models.schemas import ClaimCandidate, RetrievedCandidate
from citation_agent.retrieve.bm25 import tokenize


def select_evidence(claim: ClaimCandidate, candidate: RetrievedCandidate) -> list[str]:
    query_tokens = set(tokenize(claim.text))
    spans: list[str] = []
    for span in candidate.evidence_spans:
        span_tokens = set(tokenize(span))
        if query_tokens & span_tokens:
            spans.append(span[:280])
    return spans[:3]
