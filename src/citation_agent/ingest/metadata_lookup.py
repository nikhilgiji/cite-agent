from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from citation_agent.config import MetadataLookupConfig
from citation_agent.models.schemas import ExternalCitationSuggestion, PDFDocument


def enrich_pdf_metadata(document: PDFDocument) -> PDFDocument:
    """Placeholder for DOI/Crossref enrichment.

    Network lookup is intentionally omitted in this local-first build. The
    returned document is unchanged so the pipeline remains swappable.
    """

    return document


def search_public_metadata(
    claim_id: str,
    file_path: str,
    line_number: int,
    paragraph_index: int,
    sentence_text: str,
    config: MetadataLookupConfig,
) -> list[ExternalCitationSuggestion]:
    if not config.enabled or config.provider != "crossref":
        return []

    query = sentence_text.strip()
    if not query:
        return []

    params = urlencode(
        {
            "query.bibliographic": query[:300],
            "rows": str(config.max_results_per_claim),
        }
    )
    request = Request(
        f"https://api.crossref.org/works?{params}",
        headers={
            "User-Agent": "citation-agent/0.1 (public metadata lookup)",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=config.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8", errors="ignore"))
    except Exception:
        return []

    suggestions: list[ExternalCitationSuggestion] = []
    for index, item in enumerate(payload.get("message", {}).get("items", []), start=1):
        titles = item.get("title") or []
        title = titles[0].strip() if titles else ""
        if not title:
            continue
        authors = []
        for author in item.get("author", [])[:5]:
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            full_name = " ".join(part for part in (given, family) if part)
            if full_name:
                authors.append(full_name)
        year_parts = item.get("issued", {}).get("date-parts", [])
        year = str(year_parts[0][0]) if year_parts and year_parts[0] else None
        doi = item.get("DOI")
        score = float(item.get("score", 0.0))
        suggestions.append(
            ExternalCitationSuggestion(
                suggestion_id=f"{claim_id}-public-{index}",
                claim_id=claim_id,
                file_path=file_path,
                line_number=line_number,
                paragraph_index=paragraph_index,
                sentence_text=sentence_text,
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                url=f"https://doi.org/{doi}" if doi else item.get("URL"),
                confidence=min(score / 100.0, 1.0),
                reason="Suggested from Crossref as a potentially relevant citation not present in the local bibliography.",
                source="crossref",
            )
        )
    return suggestions
