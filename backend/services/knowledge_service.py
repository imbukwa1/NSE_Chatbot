"""SQLite-backed knowledge-base lookup for NSE educational content."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.knowledge_base import KnowledgeBaseEntry


TOKEN_RE = re.compile(r"[a-z0-9]+")
EDUCATIONAL_TERMS = {
    "bond",
    "bonds",
    "cds",
    "cdsc",
    "cma",
    "dividend",
    "dividends",
    "eps",
    "equity",
    "inflation",
    "invest",
    "investing",
    "ipo",
    "market",
    "nse",
    "pe",
    "reits",
    "roe",
    "share",
    "shares",
    "stock",
    "stocks",
    "treasury",
    "valuation",
    "yield",
}


@dataclass(frozen=True)
class KnowledgeMatch:
    entry: KnowledgeBaseEntry
    score: int


def normalize_text(value: str | None) -> str:
    return " ".join(TOKEN_RE.findall((value or "").lower()))


def _like(value: str) -> str:
    return f"%{value.lower()}%"


def _split_terms(value: str) -> list[str]:
    normalized = normalize_text(value)
    return [token for token in normalized.split() if len(token) > 2]


def _entry_answer(entry: KnowledgeBaseEntry) -> str:
    return entry.answer_markdown or entry.answer


def _entry_to_dict(entry: KnowledgeBaseEntry, score: int | None = None) -> dict[str, Any]:
    payload = {
        "id": entry.id,
        "source_id": entry.source_id,
        "slug": entry.slug,
        "category": entry.category,
        "subcategory": entry.subcategory,
        "question": entry.question,
        "aliases": entry.aliases,
        "answer": entry.answer,
        "answer_markdown": entry.answer_markdown,
        "keywords": entry.keywords,
        "difficulty": entry.difficulty,
        "related_questions": entry.related_questions,
        "source": entry.source,
        "updated_at": entry.updated_at,
    }
    if score is not None:
        payload["match_score"] = score
    return payload


class KnowledgeService:
    """Search imported KB rows without touching CSV files at runtime."""

    def __init__(self, db: Session):
        self.db = db

    def search_by_slug(self, slug: str) -> dict[str, Any] | None:
        cleaned = (slug or "").strip().lower()
        if not cleaned:
            return None
        entry = (
            self.db.query(KnowledgeBaseEntry)
            .filter(KnowledgeBaseEntry.slug == cleaned)
            .first()
        )
        return _entry_to_dict(entry, 100) if entry else None

    def search_by_alias(self, question: str) -> dict[str, Any] | None:
        return self._search_fields(question, (KnowledgeBaseEntry.aliases,), 70)

    def search_by_keywords(self, question: str) -> dict[str, Any] | None:
        return self._search_fields(question, (KnowledgeBaseEntry.keywords,), 60)

    def search(self, question: str) -> dict[str, Any] | None:
        cleaned = normalize_text(question)
        if not cleaned:
            return None

        slug_match = self.search_by_slug(cleaned.replace(" ", "-"))
        if slug_match:
            return slug_match

        terms = _split_terms(cleaned)
        filters = [
            KnowledgeBaseEntry.question.ilike(_like(cleaned)),
            KnowledgeBaseEntry.aliases.ilike(_like(cleaned)),
            KnowledgeBaseEntry.keywords.ilike(_like(cleaned)),
            KnowledgeBaseEntry.related_questions.ilike(_like(cleaned)),
        ]
        for term in terms:
            pattern = _like(term)
            filters.extend(
                [
                    KnowledgeBaseEntry.question.ilike(pattern),
                    KnowledgeBaseEntry.aliases.ilike(pattern),
                    KnowledgeBaseEntry.keywords.ilike(pattern),
                    KnowledgeBaseEntry.related_questions.ilike(pattern),
                ]
            )

        candidates = (
            self.db.query(KnowledgeBaseEntry)
            .filter(or_(*filters))
            .limit(100)
            .all()
        )
        if not candidates:
            return None

        best = max(
            (KnowledgeMatch(entry, self._score(entry, cleaned, terms)) for entry in candidates),
            key=lambda match: match.score,
        )
        return _entry_to_dict(best.entry, best.score) if best.score > 0 else None

    def _search_fields(
        self,
        question: str,
        fields: tuple[Any, ...],
        exact_weight: int,
    ) -> dict[str, Any] | None:
        cleaned = normalize_text(question)
        if not cleaned:
            return None
        terms = _split_terms(cleaned)
        filters = [field.ilike(_like(cleaned)) for field in fields]
        filters.extend(field.ilike(_like(term)) for field in fields for term in terms)
        entries = self.db.query(KnowledgeBaseEntry).filter(or_(*filters)).limit(50).all()
        if not entries:
            return None
        best = max(
            (KnowledgeMatch(entry, self._score(entry, cleaned, terms) + exact_weight) for entry in entries),
            key=lambda match: match.score,
        )
        return _entry_to_dict(best.entry, best.score)

    def _score(self, entry: KnowledgeBaseEntry, cleaned: str, terms: list[str]) -> int:
        searchable_fields = {
            "question": normalize_text(entry.question),
            "aliases": normalize_text(entry.aliases),
            "keywords": normalize_text(entry.keywords),
            "related_questions": normalize_text(entry.related_questions),
        }
        weights = {
            "question": 45,
            "aliases": 35,
            "keywords": 30,
            "related_questions": 20,
        }
        score = 0
        for field_name, text in searchable_fields.items():
            if not text:
                continue
            if cleaned == text:
                score += weights[field_name] * 3
            elif cleaned in text:
                score += weights[field_name] * 2
            score += sum(weights[field_name] for term in terms if term in text)
        return score


def is_educational_query(question: str, intent: str | None = None) -> bool:
    lowered = normalize_text(question)
    if intent in {"price_lookup", "compare", "top_movers", "market_overview", "stock_summary", "news"}:
        return False
    if intent in {"learn_mode", "dividend_info", "fundamentals"}:
        return True
    if re.search(r"\b(what|define|explain|how|why|teach|meaning|learn)\b", lowered):
        return True
    return bool(set(lowered.split()) & EDUCATIONAL_TERMS)


def build_knowledge_response(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "educational",
        "data": {
            "id": entry["id"],
            "slug": entry.get("slug"),
            "topic": entry.get("question"),
            "matched_question": entry.get("question"),
            "category": entry.get("category"),
            "subcategory": entry.get("subcategory"),
            "source": "Knowledge Base",
            "match_score": entry.get("match_score"),
        },
        "message": entry.get("answer_markdown") or entry.get("answer") or "",
        "source": "Knowledge Base",
    }
