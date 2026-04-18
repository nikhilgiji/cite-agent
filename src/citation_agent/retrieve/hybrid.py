from __future__ import annotations

from citation_agent.config import RetrievalConfig
from citation_agent.models.schemas import BibEntry, ClaimCandidate, PDFDocument, RetrievedCandidate
from citation_agent.retrieve.bm25 import lexical_overlap_score
from citation_agent.retrieve.embeddings import semantic_similarity


def retrieve_candidates(
    claim: ClaimCandidate,
    bib_entries: list[BibEntry],
    pdf_documents: list[PDFDocument],
    config: RetrievalConfig,
) -> list[RetrievedCandidate]:
    candidates: list[RetrievedCandidate] = []

    for entry in bib_entries:
        corpus = " ".join(
            [
                entry.title,
                entry.author,
                entry.fields.get("journal", ""),
                entry.fields.get("booktitle", ""),
                entry.fields.get("abstract", ""),
            ]
        )
        lexical = lexical_overlap_score(claim.text, corpus)
        semantic = semantic_similarity(claim.text, corpus)
        score = lexical * config.lexical_weight + semantic * config.semantic_weight
        if score <= 0:
            continue
        candidates.append(
            RetrievedCandidate(
                source_type="bib",
                source_id=entry.key,
                title=entry.title or entry.key,
                score=score,
                evidence_spans=[entry.title] if entry.title else [],
                metadata={"author": entry.author, "year": entry.year},
            )
        )

    for document in pdf_documents:
        corpus = " ".join([document.title or "", document.abstract or "", *document.chunks[:3]])
        lexical = lexical_overlap_score(claim.text, corpus)
        semantic = semantic_similarity(claim.text, corpus)
        score = lexical * config.lexical_weight + semantic * config.semantic_weight
        if score <= 0:
            continue
        candidates.append(
            RetrievedCandidate(
                source_type="pdf",
                source_id=document.path,
                title=document.title or document.path,
                score=score,
                evidence_spans=[chunk for chunk in document.chunks[:2] if chunk],
                metadata={"doi": document.doi or "", "path": document.path},
            )
        )

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates[: config.top_k]
