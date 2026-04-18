from __future__ import annotations

from pathlib import Path
import re

from citation_agent.models.schemas import ClaimCandidate, SourceLocation
from citation_agent.parse.claim_detection import classify_claim
from citation_agent.parse.sentence_split import split_sentences


COMMENT_PATTERN = re.compile(r"(?<!\\)%.*$")
SECTION_PATTERN = re.compile(r"\\(?:section|subsection|subsubsection)\*?\{([^}]+)\}")
CITE_PATTERN = re.compile(r"\\(?:cite|citep|citet|parencite|textcite|autocite|footcite)\w*\{[^}]+\}")
CONTROL_COMMAND_PATTERN = re.compile(
    r"\\(?:documentclass|usepackage|bibliography|bibliographystyle|addbibresource|begin|end)\b(?:\[[^\]]*\])?(?:\{[^}]*\})?"
)


def strip_comments(text: str) -> str:
    return "\n".join(COMMENT_PATTERN.sub("", line) for line in text.splitlines())


def mask_preamble_and_commands(text: str) -> str:
    begin_match = re.search(r"\\begin\{document\}", text)
    end_match = re.search(r"\\end\{document\}", text)
    masked = text
    if begin_match:
        masked = (" " * begin_match.end()) + masked[begin_match.end():]
    if end_match:
        masked = masked[: end_match.start()] + (" " * (len(masked) - end_match.start()))
    return CONTROL_COMMAND_PATTERN.sub(lambda match: " " * len(match.group(0)), masked)


def detect_existing_citation_nearby(sentence: str) -> bool:
    return bool(CITE_PATTERN.search(sentence))


def extract_claims(tex_file: Path, project_root: Path) -> list[ClaimCandidate]:
    raw = tex_file.read_text(encoding="utf-8", errors="ignore")
    text = mask_preamble_and_commands(strip_comments(raw))

    sections: list[tuple[int, str]] = [(match.start(), match.group(1).strip()) for match in SECTION_PATTERN.finditer(text)]

    def section_for_offset(offset: int) -> str | None:
        current: str | None = None
        for section_offset, name in sections:
            if section_offset > offset:
                break
            current = name
        return current

    claims: list[ClaimCandidate] = []
    paragraphs = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    running_offset = 0
    claim_counter = 1

    for paragraph_index, paragraph in enumerate(paragraphs):
        paragraph_offset = text.find(paragraph, running_offset)
        if paragraph_offset == -1:
            paragraph_offset = running_offset
        running_offset = paragraph_offset + len(paragraph)
        sentences = split_sentences(paragraph)

        for sentence_index, sentence in enumerate(sentences):
            sentence_offset = text.find(sentence, paragraph_offset)
            if sentence_offset == -1:
                sentence_offset = paragraph_offset
            section = section_for_offset(sentence_offset)
            classification, needs_citation, multi_source_hint, vague = classify_claim(sentence, section)
            has_citation = detect_existing_citation_nearby(sentence)
            claims.append(
                ClaimCandidate(
                    claim_id=f"claim-{claim_counter:05d}",
                    text=sentence,
                    classification=classification if needs_citation else "no_citation_needed",
                    needs_citation=needs_citation,
                    has_nearby_citation=has_citation,
                    multi_source_hint=multi_source_hint,
                    vague=vague,
                    location=SourceLocation(
                        file_path=str(tex_file.resolve()),
                        section=section,
                        paragraph_index=paragraph_index,
                        sentence_index=sentence_index,
                        start_offset=sentence_offset,
                        end_offset=sentence_offset + len(sentence),
                        context=paragraph[:500],
                    ),
                )
            )
            claim_counter += 1

    return claims
