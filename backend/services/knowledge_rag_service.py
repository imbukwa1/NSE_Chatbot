"""RAG utilities for the SQLite-backed knowledge base.

SQLite remains the source of truth. Pinecone stores semantic vectors and small
metadata payloads used only to find the most relevant SQLite records.
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy.orm import Session

from models.knowledge_base import KnowledgeBaseEntry
from services import pinecone_service


KB_NAMESPACE = os.getenv("PINECONE_KB_NAMESPACE", "knowledge_base")
KB_EMBEDDING_BATCH_SIZE = int(os.getenv("KB_EMBEDDING_BATCH_SIZE", "50"))
KB_RETRIEVAL_TOP_K = int(os.getenv("KB_RETRIEVAL_TOP_K", "5"))
KB_CONTEXT_MAX_CHARS = int(os.getenv("KB_CONTEXT_MAX_CHARS", "6000"))
HIGH_CONFIDENCE_THRESHOLD = 0.85
LOW_CONFIDENCE_THRESHOLD = 0.65

logger = logging.getLogger(__name__)


def build_knowledge_embedding_text(entry: KnowledgeBaseEntry) -> str:
    """Create a compact semantic representation of one KB article."""
    parts = [
        f"Question: {entry.question}",
        f"Aliases: {entry.aliases or ''}",
        f"Keywords: {entry.keywords or ''}",
        f"Related questions: {entry.related_questions or ''}",
        f"Category: {entry.category}",
        f"Subcategory: {entry.subcategory or ''}",
        f"Answer: {entry.answer_markdown or entry.answer}",
    ]
    return "\n".join(part for part in parts if part.strip())


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def vector_id_for_entry(entry: KnowledgeBaseEntry) -> str:
    return f"kb-{entry.id}"


def _metadata_for_entry(entry: KnowledgeBaseEntry, text: str) -> dict[str, Any]:
    return {
        "id": entry.id,
        "category": entry.category,
        "question": entry.question,
        "keywords": entry.keywords or "",
        "source": entry.source or "knowledge_base",
        "slug": entry.slug or "",
        "text": text[:3500],
    }


def _chunks(items: list[KnowledgeBaseEntry], size: int) -> Iterable[list[KnowledgeBaseEntry]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def entries_needing_embedding(
    db: Session,
    *,
    force: bool = False,
    limit: int | None = None,
) -> list[KnowledgeBaseEntry]:
    entries = db.query(KnowledgeBaseEntry).order_by(KnowledgeBaseEntry.id.asc()).all()
    pending: list[KnowledgeBaseEntry] = []
    for entry in entries:
        text = build_knowledge_embedding_text(entry)
        current_hash = content_hash(text)
        if force or entry.embedding_content_hash != current_hash or not entry.pinecone_vector_id:
            pending.append(entry)
            if limit and len(pending) >= limit:
                break
    return pending


def sync_knowledge_base_embeddings(
    db: Session,
    *,
    force: bool = False,
    limit: int | None = None,
    batch_size: int = KB_EMBEDDING_BATCH_SIZE,
    namespace: str = KB_NAMESPACE,
) -> dict[str, Any]:
    """Embed changed KB rows and upsert them to Pinecone."""
    pending = entries_needing_embedding(db, force=force, limit=limit)
    stats: dict[str, Any] = {
        "namespace": namespace,
        "records_seen": db.query(KnowledgeBaseEntry).count(),
        "records_pending": len(pending),
        "embedded_count": 0,
        "upserted_count": 0,
        "skipped_count": 0,
    }
    if not pending:
        return stats

    model = pinecone_service.DEFAULT_EMBEDDING_MODEL
    for batch in _chunks(pending, max(batch_size, 1)):
        texts = [build_knowledge_embedding_text(entry) for entry in batch]
        hashes = [content_hash(text) for text in texts]
        embeddings = pinecone_service.embed_texts(texts)
        vectors = []
        for entry, text, text_hash, embedding in zip(batch, texts, hashes, embeddings):
            vector_id = vector_id_for_entry(entry)
            vectors.append(
                {
                    "id": vector_id,
                    "values": embedding,
                    "metadata": _metadata_for_entry(entry, text),
                }
            )
            entry.embedding_model = model
            entry.embedding_content_hash = text_hash
            entry.pinecone_vector_id = vector_id
            entry.pinecone_synced_at = datetime.now(timezone.utc)

        result = pinecone_service.upsert_vectors(vectors, namespace=namespace)
        stats["embedded_count"] += len(embeddings)
        stats["upserted_count"] += result.get("upserted_count", 0)

    stats["skipped_count"] = max(stats["records_seen"] - stats["records_pending"], 0)
    db.commit()
    return stats


def _match_metadata(match) -> dict[str, Any]:
    if isinstance(match, dict):
        return match.get("metadata", {}) or {}
    return getattr(match, "metadata", {}) or {}


def _match_score(match) -> float:
    if isinstance(match, dict):
        return float(match.get("score") or 0)
    return float(getattr(match, "score", 0) or 0)


def _match_vector_id(match) -> str | None:
    if isinstance(match, dict):
        return match.get("id")
    return getattr(match, "id", None)


def retrieve_knowledge_context(
    db: Session,
    query: str,
    *,
    top_k: int = KB_RETRIEVAL_TOP_K,
    namespace: str = KB_NAMESPACE,
) -> dict[str, Any]:
    """Retrieve top semantic KB matches from Pinecone and hydrate from SQLite."""
    if not query.strip():
        return {"matches": [], "top_score": 0.0, "confidence": "none", "context": ""}

    try:
        index = pinecone_service.get_index()
        query_embedding = pinecone_service.embed_texts([query])[0]
        response = index.query(
            namespace=namespace,
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
        )
    except Exception as exc:
        logger.warning("Knowledge RAG retrieval unavailable: %s", exc)
        return {
            "matches": [],
            "top_score": 0.0,
            "confidence": "unavailable",
            "context": "",
            "error": str(exc),
        }

    response_matches = response.get("matches", []) if isinstance(response, dict) else getattr(response, "matches", [])
    hydrated_matches: list[dict[str, Any]] = []
    for match in response_matches or []:
        metadata = _match_metadata(match)
        entry_id = metadata.get("id")
        if not entry_id:
            vector_id = _match_vector_id(match) or ""
            entry_id = vector_id.removeprefix("kb-") if vector_id.startswith("kb-") else None
        if not entry_id:
            continue
        entry = db.get(KnowledgeBaseEntry, int(entry_id))
        if not entry:
            continue
        hydrated_matches.append(
            {
                "id": entry.id,
                "score": _match_score(match),
                "category": entry.category,
                "question": entry.question,
                "keywords": entry.keywords,
                "source": entry.source,
                "answer": entry.answer_markdown or entry.answer,
            }
        )

    top_score = hydrated_matches[0]["score"] if hydrated_matches else 0.0
    return {
        "matches": hydrated_matches,
        "top_score": top_score,
        "confidence": confidence_label(top_score),
        "context": build_rag_context(hydrated_matches),
    }


def confidence_label(score: float) -> str:
    if score >= HIGH_CONFIDENCE_THRESHOLD:
        return "high"
    if score >= LOW_CONFIDENCE_THRESHOLD:
        return "medium"
    return "low"


def confidence_notice(score: float) -> str:
    if score >= HIGH_CONFIDENCE_THRESHOLD:
        return "Answer confidently using the supplied knowledge-base context."
    if score >= LOW_CONFIDENCE_THRESHOLD:
        return (
            "The retrieved context is somewhat relevant but not perfect. Start with a brief "
            "lower-confidence notice and avoid overstating certainty."
        )
    return (
        "The retrieved context is weak. Ask a concise clarification question or provide only "
        "general guidance if the answer is obvious from the conversation."
    )


def build_rag_context(matches: list[dict[str, Any]], max_chars: int = KB_CONTEXT_MAX_CHARS) -> str:
    blocks = []
    for position, match in enumerate(matches, start=1):
        blocks.append(
            (
                f"[KB {position}] id={match['id']} score={match['score']:.3f}\n"
                f"Category: {match['category']}\n"
                f"Question: {match['question']}\n"
                f"Keywords: {match.get('keywords') or ''}\n"
                f"Answer:\n{match['answer']}"
            ).strip()
        )
    context = "\n\n---\n\n".join(blocks)
    return context[:max_chars]


def build_grounded_prompt(
    *,
    question: str,
    context: str,
    top_score: float,
    conversation_context: str | None = None,
) -> str:
    memory = (
        f"Recent conversation context:\n{conversation_context.strip()}\n\n"
        if conversation_context and conversation_context.strip()
        else ""
    )
    return (
        "Answer the user's NSE education question using only the knowledge-base context below. "
        "Do not invent facts that are not supported by the context. Keep the answer concise, "
        "use plain investor-friendly language, and avoid repeating prior information unless it "
        "is needed for continuity.\n\n"
        f"{confidence_notice(top_score)}\n\n"
        f"{memory}"
        f"Knowledge-base context:\n{context}\n\n"
        f"User question: {question}"
    )
