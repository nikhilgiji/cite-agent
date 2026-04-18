from __future__ import annotations

from pathlib import Path

from citation_agent.models.schemas import ExistingCitationResult


def render_existing_citation_text_report(results: list[ExistingCitationResult]) -> str:
    lines: list[str] = ["Citation Verification Report", ""]
    if not results:
        lines.append("No existing citation commands were found.")
        return "\n".join(lines) + "\n"

    status_counts: dict[str, int] = {}
    for result in results:
        status_counts[result.status] = status_counts.get(result.status, 0) + 1

    lines.extend(
        [
            f"Total checks: {len(results)}",
            f"Supported: {status_counts.get('supported', 0)}",
            f"Weak support: {status_counts.get('weak_support', 0)}",
            f"Unsupported: {status_counts.get('unsupported', 0)}",
            f"Missing keys: {status_counts.get('missing_key', 0)}",
            "",
        ]
    )

    for result in results:
        lines.extend(
            [
                f"[{result.check_id}] {result.status.upper()}",
                f"File: {result.file_path}",
                f"Line: {result.line_number}",
                f"Citation: \\{result.citation_command}{{{', '.join(result.cited_keys)}}}",
                f"Confidence: {result.confidence:.2f}",
                f"Sentence: {result.sentence_text}",
                f"Reason: {result.reason}",
            ]
        )
        if result.missing_keys:
            lines.append(f"Missing keys: {', '.join(result.missing_keys)}")
        if result.evidence_spans:
            lines.append(f"Evidence: {' | '.join(result.evidence_spans[:3])}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_existing_citation_text_report(path: str | Path, results: list[ExistingCitationResult]) -> None:
    Path(path).write_text(render_existing_citation_text_report(results), encoding="utf-8")
