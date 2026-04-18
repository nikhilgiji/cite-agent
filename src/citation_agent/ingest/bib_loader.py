from __future__ import annotations

from pathlib import Path
import re

from citation_agent.models.schemas import BibEntry


ENTRY_START_PATTERN = re.compile(r"@(?P<type>\w+)\s*\{\s*(?P<key>[^,]+)\s*,", re.IGNORECASE)
FIELD_PATTERN = re.compile(r"(?P<name>\w+)\s*=\s*(?P<value>\{(?:[^{}]|\{[^{}]*\})*\}|\"[^\"]*\"|[^,\n]+)", re.IGNORECASE)


def _clean_value(value: str) -> str:
    cleaned = value.strip().rstrip(",").strip()
    if (cleaned.startswith("{") and cleaned.endswith("}")) or (cleaned.startswith('"') and cleaned.endswith('"')):
        return cleaned[1:-1].strip()
    return cleaned


def parse_bib_file(path: str | Path) -> list[BibEntry]:
    bib_path = Path(path).resolve()
    if not bib_path.exists():
        return []

    text = bib_path.read_text(encoding="utf-8", errors="ignore")
    entries: list[BibEntry] = []
    for match in ENTRY_START_PATTERN.finditer(text):
        start = match.start()
        next_match = ENTRY_START_PATTERN.search(text, match.end())
        entry_text = text[start: next_match.start() if next_match else len(text)]
        fields = {
            field_match.group("name").lower(): _clean_value(field_match.group("value"))
            for field_match in FIELD_PATTERN.finditer(entry_text)
        }
        malformed = "title" not in fields or "author" not in fields
        entries.append(
            BibEntry(
                entry_type=match.group("type").lower(),
                key=match.group("key").strip(),
                fields=fields,
                source_path=str(bib_path),
                malformed=malformed,
            )
        )
    return entries


def load_bib_entries(paths: list[str]) -> list[BibEntry]:
    deduped: dict[str, BibEntry] = {}
    for path in paths:
        for entry in parse_bib_file(path):
            deduped.setdefault(entry.key, entry)
    return list(deduped.values())
