from __future__ import annotations

from pathlib import Path
import re

from citation_agent.models.schemas import ClaimCandidate, ExistingCitationCheck, SourceLocation
from citation_agent.parse.claim_detection import classify_claim
from citation_agent.parse.sentence_split import split_sentences


COMMENT_PATTERN = re.compile(r"(?<!\\)%.*$")
SECTION_PATTERN = re.compile(r"\\(?:section|subsection|subsubsection)\*?\{([^}]+)\}")
CITE_PATTERN = re.compile(r"\\(?:cite|citep|citet|parencite|textcite|autocite|footcite)\w*\{[^}]+\}")
CAPTURE_CITE_PATTERN = re.compile(r"\\(?P<command>(?:cite|citep|citet|parencite|textcite|autocite|footcite)\w*)\{(?P<keys>[^}]+)\}")
CONTROL_COMMAND_PATTERN = re.compile(
    r"\\(?:documentclass|usepackage|bibliography|bibliographystyle|addbibresource|begin|end)\b(?:\[[^\]]*\])?(?:\{[^}]*\})?"
)
NON_PROSE_COMMAND_PATTERN = re.compile(
    r"\\(?:chapter|section|subsection|subsubsection|paragraph|subparagraph|label|ref|eqref|pageref|include|input|subfile|includegraphics|caption|item|texttt|path|print[a-zA-Z]*|nomentry[a-zA-Z]*|appendix[a-zA-Z]*|tableofcontents|listoffigures|listoftables)\b"
)
NON_PROSE_TOKEN_PATTERN = re.compile(r"(results/|scripts/|repository root|\.png\b|\.jpg\b|\.pdf\b|\.bib\b)", re.IGNORECASE)


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


def looks_like_prose_sentence(sentence: str) -> bool:
    without_cites = CAPTURE_CITE_PATTERN.sub("", sentence)
    if NON_PROSE_COMMAND_PATTERN.search(without_cites):
        return False
    if NON_PROSE_TOKEN_PATTERN.search(without_cites):
        return False
    return True


def _document_body(text: str) -> str:
    begin_match = re.search(r"\\begin\{document\}", text)
    end_match = re.search(r"\\end\{document\}", text)
    start = begin_match.end() if begin_match else 0
    end = end_match.start() if end_match else len(text)
    return text[start:end]


def _section_lookup(text: str) -> list[tuple[int, str]]:
    return [(match.start(), match.group(1).strip()) for match in SECTION_PATTERN.finditer(text)]


def _section_for_offset(sections: list[tuple[int, str]], offset: int) -> str | None:
    current: str | None = None
    for section_offset, name in sections:
        if section_offset > offset:
            break
        current = name
    return current


def _line_number_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, max(offset, 0)) + 1


def _document_bounds(text: str) -> tuple[int, int]:
    begin_match = re.search(r"\\begin\{document\}", text)
    end_match = re.search(r"\\end\{document\}", text)
    start = begin_match.end() if begin_match else 0
    end = end_match.start() if end_match else len(text)
    return start, end


def extract_claims(tex_file: Path, project_root: Path) -> list[ClaimCandidate]:
    raw = tex_file.read_text(encoding="utf-8", errors="ignore")
    text = mask_preamble_and_commands(strip_comments(raw))
    sections = _section_lookup(text)

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
            section = _section_for_offset(sections, sentence_offset)
            if not looks_like_prose_sentence(sentence):
                classification = "non_prose"
                needs_citation = False
                multi_source_hint = False
                vague = False
            else:
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
                        line_number=_line_number_for_offset(text, sentence_offset),
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


def extract_existing_citation_checks(tex_file: Path) -> list[ExistingCitationCheck]:
    raw = tex_file.read_text(encoding="utf-8", errors="ignore")
    text = strip_comments(raw)
    body_start, body_end = _document_bounds(text)
    body = text[body_start:body_end]
    sections = _section_lookup(body)

    checks: list[ExistingCitationCheck] = []
    paragraphs = [block.strip() for block in re.split(r"\n\s*\n", body) if block.strip()]
    running_offset = 0
    check_counter = 1

    for paragraph_index, paragraph in enumerate(paragraphs):
        paragraph_offset = body.find(paragraph, running_offset)
        if paragraph_offset == -1:
            paragraph_offset = running_offset
        running_offset = paragraph_offset + len(paragraph)
        sentences = split_sentences(paragraph)

        for sentence_index, sentence in enumerate(sentences):
            matches = list(CAPTURE_CITE_PATTERN.finditer(sentence))
            if not matches:
                continue
            if not looks_like_prose_sentence(sentence):
                continue
            sentence_offset = body.find(sentence, paragraph_offset)
            if sentence_offset == -1:
                sentence_offset = paragraph_offset
            cleaned_sentence = CAPTURE_CITE_PATTERN.sub("", sentence)
            cleaned_sentence = " ".join(cleaned_sentence.split()).strip()
            section = _section_for_offset(sections, sentence_offset)
            for match in matches:
                cited_keys = [key.strip() for key in match.group("keys").split(",") if key.strip()]
                full_sentence_offset = body_start + sentence_offset
                checks.append(
                    ExistingCitationCheck(
                        check_id=f"existing-{check_counter:05d}",
                        citation_command=match.group("command"),
                        cited_keys=cited_keys,
                        sentence_text=sentence.strip(),
                        cleaned_claim_text=cleaned_sentence,
                        location=SourceLocation(
                            file_path=str(tex_file.resolve()),
                            line_number=_line_number_for_offset(text, full_sentence_offset),
                            section=section,
                            paragraph_index=paragraph_index,
                            sentence_index=sentence_index,
                            start_offset=full_sentence_offset,
                            end_offset=full_sentence_offset + len(sentence),
                            context=paragraph[:500],
                        ),
                    )
                )
                check_counter += 1

    return checks
