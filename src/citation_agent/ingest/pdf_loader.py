from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re

from citation_agent.models.schemas import PDFDocument


DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)


def _filename_title(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").strip()


def _extract_text_heuristic(pdf_path: Path) -> tuple[list[str], str | None]:
    raw = pdf_path.read_bytes()[:200_000]
    decoded = raw.decode("latin-1", errors="ignore")
    lines = [line.strip() for line in decoded.splitlines() if len(line.strip()) > 20]
    chunks = [" ".join(lines[i: i + 4])[:700] for i in range(0, min(len(lines), 40), 4)]
    doi_match = DOI_PATTERN.search(decoded)
    return chunks[:10], doi_match.group(0) if doi_match else None


def load_pdfs(pdf_dir: str | Path | None) -> list[PDFDocument]:
    if pdf_dir is None:
        return []
    root = Path(pdf_dir).resolve()
    if not root.exists():
        return []

    documents: list[PDFDocument] = []
    for pdf_path in sorted(root.rglob("*.pdf")):
        chunks, doi = _extract_text_heuristic(pdf_path)
        checksum = sha256(pdf_path.read_bytes()).hexdigest()
        documents.append(
            PDFDocument(
                path=str(pdf_path),
                checksum=checksum,
                title=_filename_title(pdf_path) or pdf_path.name,
                chunks=chunks,
                doi=doi,
            )
        )
    return documents
