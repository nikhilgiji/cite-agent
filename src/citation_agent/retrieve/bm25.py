from __future__ import annotations

import math
import re


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def lexical_overlap_score(query: str, document: str) -> float:
    query_tokens = tokenize(query)
    doc_tokens = tokenize(document)
    if not query_tokens or not doc_tokens:
        return 0.0

    doc_freq: dict[str, int] = {}
    for token in doc_tokens:
        doc_freq[token] = doc_freq.get(token, 0) + 1

    score = 0.0
    doc_len = len(doc_tokens)
    for token in query_tokens:
        tf = doc_freq.get(token, 0)
        if not tf:
            continue
        score += (tf / doc_len) * (1.0 + math.log1p(tf))

    return min(score * 8.0, 1.0)
