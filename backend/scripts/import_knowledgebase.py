"""Import educational Q&A CSV files into the SQLite knowledge base.

This script is intentionally import-safe: it can be called from the CLI or from
the admin API, and duplicate CSV rows are skipped by CSV id or slug.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import database
from models.knowledge_base import KnowledgeBaseEntry


def _knowledgebase_dir(explicit_path: str | None = None) -> Path:
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()

    candidates = (
        PROJECT_ROOT / "knowledgebase",
        PROJECT_ROOT / "knowledge base",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _clean(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def _existing_filter(row: dict[str, str]):
    source_id = _clean(row, "id")
    slug = _clean(row, "slug").lower()
    filters = []
    if source_id:
        filters.append(KnowledgeBaseEntry.source_id == source_id)
    if slug:
        filters.append(func.lower(KnowledgeBaseEntry.slug) == slug)
    return or_(*filters) if filters else None


def _entry_from_row(row: dict[str, str]) -> KnowledgeBaseEntry:
    answer_markdown = _clean(row, "answer_markdown")
    answer = answer_markdown or _clean(row, "answer")
    return KnowledgeBaseEntry(
        source_id=_clean(row, "id") or None,
        slug=_clean(row, "slug").lower() or None,
        category=_clean(row, "category") or "General",
        subcategory=_clean(row, "subcategory") or None,
        question=_clean(row, "question"),
        aliases=_clean(row, "aliases") or None,
        answer=answer,
        answer_markdown=answer_markdown or None,
        keywords=_clean(row, "keywords") or None,
        difficulty=_clean(row, "difficulty") or None,
        related_questions=_clean(row, "related_questions") or None,
        source=_clean(row, "source") or "knowledgebase_csv",
        created_by=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _record_import(db: Session, stats: dict[str, Any]) -> None:
    db.execute(
        text(
            """
            INSERT INTO knowledge_base_imports
                (files_scanned, rows_seen, imported_count, skipped_count, status)
            VALUES
                (:files_scanned, :rows_seen, :imported_count, :skipped_count, :status)
            """
        ),
        stats,
    )


def import_knowledgebase(
    knowledgebase_path: str | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    database.init_db()
    kb_dir = _knowledgebase_dir(knowledgebase_path)
    stats: dict[str, Any] = {
        "knowledgebase_path": str(kb_dir),
        "files_scanned": 0,
        "rows_seen": 0,
        "imported_count": 0,
        "skipped_count": 0,
        "status": "success",
    }

    if not kb_dir.exists():
        stats["status"] = "missing_directory"
        if db is None:
            with database.SessionLocal() as local_db:
                _record_import(local_db, stats)
                local_db.commit()
        else:
            _record_import(db, stats)
            db.commit()
        return stats

    owns_session = db is None
    session = db or database.SessionLocal()
    try:
        for csv_path in sorted(kb_dir.rglob("*.csv")):
            stats["files_scanned"] += 1
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    stats["rows_seen"] += 1
                    question = _clean(row, "question")
                    answer = _clean(row, "answer_markdown") or _clean(row, "answer")
                    duplicate_filter = _existing_filter(row)
                    if not question or not answer:
                        stats["skipped_count"] += 1
                        continue
                    if duplicate_filter is not None:
                        exists = session.query(KnowledgeBaseEntry.id).filter(duplicate_filter).first()
                        if exists:
                            stats["skipped_count"] += 1
                            continue
                    session.add(_entry_from_row(row))
                    stats["imported_count"] += 1

        _record_import(session, stats)
        session.commit()
        return stats
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import NSE knowledge-base CSV files.")
    parser.add_argument("--path", help="Optional path to knowledgebase directory.")
    args = parser.parse_args()
    stats = import_knowledgebase(args.path)
    print(stats)


if __name__ == "__main__":
    main()
