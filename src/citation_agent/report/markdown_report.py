from __future__ import annotations

from citation_agent.models.schemas import PipelineArtifacts


def render_markdown_report(artifacts: PipelineArtifacts) -> str:
    lines: list[str] = [
        "# Citation Agent Report",
        "",
        "## Project Summary",
        f"- Project root: `{artifacts.analysis.project_root}`",
        f"- Main TeX file: `{artifacts.analysis.main_tex or 'not found'}`",
        f"- TeX files analyzed: {len(artifacts.analysis.tex_files)}",
        f"- Bibliography files: {len(artifacts.analysis.bibliography_files)}",
        f"- PDFs ingested: {len(artifacts.pdf_documents)}",
        "",
        "## Citation Actions",
    ]

    inserted = [decision for decision in artifacts.decisions if decision.action == "inserted"]
    review = [decision for decision in artifacts.decisions if decision.action == "needs_review"]

    if inserted:
        for decision in inserted[:50]:
            lines.append(
                f"- `{decision.claim_id}` inserted `{decision.citation_command}` with keys `{', '.join(decision.bib_keys)}` (confidence {decision.confidence:.2f})"
            )
    else:
        lines.append("- No citations were auto-inserted.")

    lines.extend(["", "## Needs Review"])
    if review:
        for decision in review[:50]:
            lines.append(f"- `{decision.claim_id}`: {decision.reason}")
    else:
        lines.append("- No review items.")

    lines.extend(["", "## Validation"])
    if artifacts.validation_messages:
        lines.extend(f"- {message}" for message in artifacts.validation_messages)
    else:
        lines.append("- No validation warnings.")

    return "\n".join(lines) + "\n"
