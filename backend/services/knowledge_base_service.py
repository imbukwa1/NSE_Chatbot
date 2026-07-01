"""Backward-compatible facade for the SQLite knowledge service."""

from __future__ import annotations

from typing import Any

from database import SessionLocal
from services.knowledge_service import KnowledgeService, build_knowledge_response


def answer_knowledge_question(query: str) -> dict[str, Any] | None:
    """Return a KB answer from SQLite only; CSV files are never read here."""
    with SessionLocal() as db:
        match = KnowledgeService(db).search(query)
        if not match:
            return None
        return build_knowledge_response(match)
