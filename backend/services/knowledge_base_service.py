"""Local knowledge-base search for beginner NSE education questions."""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any

from services.knowledge_base_generator import DATA_PATH, write_entries


PLURAL_NORMALIZATIONS = (
    (r"\bdividends\b", "dividend"),
    (r"\bshares\b", "share"),
    (r"\bstocks\b", "stock"),
    (r"\bbonds\b", "bond"),
    (r"\bcompanies\b", "company"),
    (r"\bsecurities\b", "security"),
)


def normalize_query(text: str) -> str:
    normalized = text.lower()
    normalized = re.sub(r"[^a-z0-9\s/]", " ", normalized)
    for pattern, replacement in PLURAL_NORMALIZATIONS:
        normalized = re.sub(pattern, replacement, normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _tokens(text: str) -> set[str]:
    return {token for token in normalize_query(text).split() if len(token) > 2}


@lru_cache(maxsize=1)
def load_knowledge_base() -> list[dict[str, Any]]:
    if not DATA_PATH.exists():
        write_entries(DATA_PATH)
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def find_best_entry(query: str, min_score: float = 0.42) -> dict[str, Any] | None:
    normalized_query = normalize_query(query)
    query_tokens = _tokens(query)
    if not normalized_query or not query_tokens:
        return None

    best_entry = None
    best_score = 0.0

    for entry in load_knowledge_base():
        question = normalize_query(entry["question"])
        keywords = {normalize_query(keyword) for keyword in entry.get("keywords", [])}
        keyword_tokens = set().union(*(_tokens(keyword) for keyword in keywords)) if keywords else set()
        entry_tokens = _tokens(question) | keyword_tokens

        overlap = len(query_tokens & entry_tokens) / max(len(query_tokens), 1)
        similarity = SequenceMatcher(None, normalized_query, question).ratio()
        keyword_bonus = 0.15 if normalized_query in keywords else 0
        score = (overlap * 0.65) + (similarity * 0.35) + keyword_bonus

        if score > best_score:
            best_score = score
            best_entry = entry

    if best_score < min_score:
        return None

    return {**best_entry, "score": round(best_score, 3)}


def answer_knowledge_question(query: str) -> dict[str, Any] | None:
    entry = find_best_entry(query)
    if not entry:
        return None

    topic = normalize_query(entry["question"])
    for prefix in ("what is ", "what are ", "explain ", "define "):
        if topic.startswith(prefix):
            topic = topic[len(prefix):]
            break
    for article in ("a ", "an ", "the "):
        if topic.startswith(article):
            topic = topic[len(article):]
            break
    topic = topic.strip() or entry["question"]

    return {
        "type": "educational",
        "data": {
            "topic": topic,
            "matched_question": entry["question"],
            "category": entry["category"],
            "source": "generated_knowledge_base",
            "match_score": entry["score"],
        },
        "message": entry["answer"],
    }
