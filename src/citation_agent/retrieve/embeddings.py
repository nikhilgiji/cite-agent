from __future__ import annotations

from citation_agent.retrieve.bm25 import tokenize


def semantic_similarity(query: str, document: str) -> float:
    query_tokens = set(tokenize(query))
    doc_tokens = set(tokenize(document))
    if not query_tokens or not doc_tokens:
        return 0.0
    intersection = len(query_tokens & doc_tokens)
    union = len(query_tokens | doc_tokens)
    return intersection / union
