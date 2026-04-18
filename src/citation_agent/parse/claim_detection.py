from __future__ import annotations

import re


CLAIM_HINTS: list[tuple[str, str]] = [
    (r"\b(state[- ]of[- ]the[- ]art|sota|benchmark|outperforms?|improves?|accuracy|f1|bleu)\b", "benchmark_result"),
    (r"\b(proposed by|introduced in|presented by|described by)\b", "method_attribution"),
    (r"\b(widely used|common|popular|standard|de facto)\b", "dataset_software_standard"),
    (r"\b(according to|as shown in|prior work|previous studies|related work)\b", "related_work"),
    (r"\b(\d{4})\b", "historical"),
    (r"\b(is defined as|refers to|we define|can be defined)\b", "definitional"),
]

MULTI_SOURCE_HINTS = re.compile(r"\b(several|many|various|multiple|studies|systems|approaches)\b", re.IGNORECASE)
VAGUE_HINTS = re.compile(r"\b(often|usually|typically|generally|somewhat|many believe)\b", re.IGNORECASE)
NEEDS_CITATION_HINTS = re.compile(
    r"\b(widely used|state[- ]of[- ]the[- ]art|proposed|introduced|according to|benchmark|standard|dataset|model|framework|library|software|year|survey)\b",
    re.IGNORECASE,
)


def classify_claim(sentence: str, section: str | None) -> tuple[str, bool, bool, bool]:
    lowered = sentence.lower()
    classification = "background_factual_claim"
    for pattern, label in CLAIM_HINTS:
        if re.search(pattern, lowered, re.IGNORECASE):
            classification = label
            break

    if section and any(marker in section.lower() for marker in ("related work", "background", "prior work")):
        classification = "related_work"

    needs_citation = bool(NEEDS_CITATION_HINTS.search(sentence))
    if any(ch.isdigit() for ch in sentence):
        needs_citation = True

    multi_source_hint = bool(MULTI_SOURCE_HINTS.search(sentence))
    vague = bool(VAGUE_HINTS.search(sentence))
    return classification, needs_citation, multi_source_hint, vague
