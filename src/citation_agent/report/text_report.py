from __future__ import annotations

from pathlib import Path

from citation_agent.models.schemas import ExistingCitationResult, PipelineArtifacts


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
                f"Paragraph: {result.paragraph_index + 1}",
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


def render_review_text_report(artifacts: PipelineArtifacts, mode: str = "review") -> str:
    lines: list[str] = [
        f"Citation Agent {mode.title()} Report",
        "",
        f"Project root: {artifacts.analysis.project_root}",
        f"Main TeX file: {artifacts.analysis.main_tex or 'not found'}",
        f"TeX files analyzed: {len(artifacts.analysis.tex_files)}",
        f"PDFs ingested: {len(artifacts.pdf_documents)}",
        "",
    ]

    supported = [item for item in artifacts.existing_citation_results if item.status == "supported"]
    weak = [item for item in artifacts.existing_citation_results if item.status == "weak_support"]
    invalid = [item for item in artifacts.existing_citation_results if item.status in {"unsupported", "missing_key"}]
    inserted = [decision for decision in artifacts.decisions if decision.action == "inserted"]
    review_needed = [decision for decision in artifacts.decisions if decision.action == "needs_review"]
    claim_by_id = {claim.claim_id: claim for claim in artifacts.claims}

    lines.extend(
        [
            "Summary",
            f"- Existing citations supported: {len(supported)}",
            f"- Existing citations weak support: {len(weak)}",
            f"- Existing citations invalid or incorrect: {len(invalid)}",
            f"- Missing citations that can be added automatically: {len(inserted)}",
            f"- Claims still needing manual review: {len(review_needed)}",
            f"- Public citation suggestions: {len(artifacts.external_suggestions)}",
            "",
        ]
    )

    def add_existing_block(title: str, items: list[ExistingCitationResult], limit: int = 80) -> None:
        lines.append(title)
        if not items:
            lines.append("- None")
            lines.append("")
            return
        for item in items[:limit]:
            lines.extend(
                [
                    f"- File: {item.file_path}",
                    f"  Line: {item.line_number}, Paragraph: {item.paragraph_index + 1}",
                    f"  Status: {item.status}",
                    f"  Citation: \\{item.citation_command}{{{', '.join(item.cited_keys)}}}",
                    f"  Confidence: {item.confidence:.2f}",
                    f"  Sentence: {item.sentence_text}",
                    f"  Reason: {item.reason}",
                ]
            )
            if item.missing_keys:
                lines.append(f"  Missing keys: {', '.join(item.missing_keys)}")
            if item.evidence_spans:
                lines.append(f"  Evidence: {' | '.join(item.evidence_spans[:2])}")
        lines.append("")

    add_existing_block("Valid existing citations", supported)
    add_existing_block("Weak-support existing citations to review but keep", weak)
    add_existing_block("Invalid or incorrect existing citations", invalid)

    lines.append("Missing citations that can be added")
    if not inserted:
        lines.append("- None")
    else:
        for decision in inserted[:120]:
            claim = claim_by_id.get(decision.claim_id)
            if not claim:
                continue
            lines.extend(
                [
                    f"- File: {claim.location.file_path}",
                    f"  Line: {claim.location.line_number}, Paragraph: {claim.location.paragraph_index + 1}",
                    f"  Sentence: {claim.text}",
                    f"  Add citation: \\{decision.citation_command or 'cite'}{{{', '.join(decision.bib_keys)}}}",
                    f"  Confidence: {decision.confidence:.2f}",
                    f"  Reason: {decision.reason}",
                ]
            )
            if decision.evidence_spans:
                lines.append(f"  Evidence: {' | '.join(decision.evidence_spans[:2])}")
    lines.append("")

    lines.append("Claims still needing review")
    if not review_needed:
        lines.append("- None")
    else:
        for decision in review_needed[:120]:
            claim = claim_by_id.get(decision.claim_id)
            if not claim:
                continue
            lines.extend(
                [
                    f"- File: {claim.location.file_path}",
                    f"  Line: {claim.location.line_number}, Paragraph: {claim.location.paragraph_index + 1}",
                    f"  Sentence: {claim.text}",
                    f"  Reason: {decision.reason}",
                ]
            )
    lines.append("")

    lines.append("Additional public citation suggestions")
    if not artifacts.external_suggestions:
        lines.append("- None")
    else:
        for suggestion in artifacts.external_suggestions[:150]:
            author_text = ", ".join(suggestion.authors[:3]) if suggestion.authors else "unknown authors"
            lines.extend(
                [
                    f"- File: {suggestion.file_path}",
                    f"  Line: {suggestion.line_number}, Paragraph: {suggestion.paragraph_index + 1}",
                    f"  Sentence: {suggestion.sentence_text}",
                    f"  Suggested source: {suggestion.title}",
                    f"  Authors: {author_text}",
                    f"  Year: {suggestion.year or 'unknown'}",
                    f"  DOI: {suggestion.doi or 'n/a'}",
                    f"  URL: {suggestion.url or 'n/a'}",
                    f"  Confidence: {suggestion.confidence:.2f}",
                    f"  Reason: {suggestion.reason}",
                ]
            )
    lines.append("")

    lines.append("Validation warnings")
    if artifacts.validation_messages:
        lines.extend(f"- {message}" for message in artifacts.validation_messages)
    else:
        lines.append("- None")

    return "\n".join(lines).rstrip() + "\n"


def write_review_text_report(path: str | Path, artifacts: PipelineArtifacts, mode: str = "review") -> None:
    Path(path).write_text(render_review_text_report(artifacts, mode=mode), encoding="utf-8")
