from __future__ import annotations

import re


SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\\])")


def split_sentences(paragraph: str) -> list[str]:
    text = " ".join(paragraph.split())
    if not text:
        return []
    return [part.strip() for part in SENTENCE_BOUNDARY.split(text) if part.strip()]
