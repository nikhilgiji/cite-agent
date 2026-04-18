from __future__ import annotations

from citation_agent.models.schemas import BibEntry, CitationDecision


def run_sanity_checks(decisions: list[CitationDecision], bib_entries: list[BibEntry]) -> list[str]:
    messages: list[str] = []
    known_keys = {entry.key for entry in bib_entries}
    for decision in decisions:
        if decision.action != "inserted":
            continue
        missing = [key for key in decision.bib_keys if key not in known_keys and key not in {entry.key for entry in decision.new_bib_entries}]
        if missing:
            messages.append(f"{decision.claim_id}: inserted citation references missing keys {missing}")
        if not decision.citation_command:
            messages.append(f"{decision.claim_id}: inserted citation has no command")
    return messages
