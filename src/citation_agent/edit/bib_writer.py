from __future__ import annotations

from pathlib import Path

from citation_agent.models.schemas import BibEntry


def format_bib_entry(entry: BibEntry) -> str:
    fields = ",\n".join(f"  {name} = {{{value}}}" for name, value in sorted(entry.fields.items()))
    return f"@{entry.entry_type}{{{entry.key},\n{fields}\n}}\n"


def append_bib_entries(path: str | Path, entries: list[BibEntry]) -> None:
    if not entries:
        return
    bib_path = Path(path)
    existing = bib_path.read_text(encoding="utf-8", errors="ignore") if bib_path.exists() else ""
    new_text = existing.rstrip() + "\n\n" + "\n".join(format_bib_entry(entry).rstrip() for entry in entries) + "\n"
    bib_path.write_text(new_text, encoding="utf-8")
