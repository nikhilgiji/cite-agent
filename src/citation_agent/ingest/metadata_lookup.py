from __future__ import annotations

from citation_agent.models.schemas import PDFDocument


def enrich_pdf_metadata(document: PDFDocument) -> PDFDocument:
    """Placeholder for DOI/Crossref enrichment.

    Network lookup is intentionally omitted in this local-first build. The
    returned document is unchanged so the pipeline remains swappable.
    """

    return document
