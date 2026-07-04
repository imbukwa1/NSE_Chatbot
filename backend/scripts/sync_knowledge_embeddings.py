"""Generate KB embeddings and sync them to Pinecone."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import database
from services.knowledge_rag_service import sync_knowledge_base_embeddings


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync SQLite knowledge base embeddings to Pinecone.")
    parser.add_argument("--force", action="store_true", help="Re-embed every KB article.")
    parser.add_argument("--limit", type=int, default=None, help="Optional max records to sync.")
    parser.add_argument("--batch-size", type=int, default=50, help="Embedding/upsert batch size.")
    args = parser.parse_args()

    database.init_db()
    with database.SessionLocal() as db:
        stats = sync_knowledge_base_embeddings(
            db,
            force=args.force,
            limit=args.limit,
            batch_size=args.batch_size,
        )
    print(stats)


if __name__ == "__main__":
    main()
