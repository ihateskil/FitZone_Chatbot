#!/usr/bin/env python3
"""Rebuild the Knowledge_db search index cache."""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import CACHE_DIR, KNOWLEDGE_DB_DIR  # noqa: E402
from src.knowledge_retriever import KnowledgeRetriever  # noqa: E402


def main() -> int:
    cache_file = CACHE_DIR / "knowledge_chunks.json"
    if cache_file.exists():
        cache_file.unlink()
        print(f"Removed stale cache: {cache_file}")

    if not KNOWLEDGE_DB_DIR.is_dir():
        print(f"ERROR: Knowledge_db not found at {KNOWLEDGE_DB_DIR}")
        return 1

    pdf_count = len(list(KNOWLEDGE_DB_DIR.glob("*.pdf")))
    print(f"Indexing {pdf_count} PDFs + gym_calculations.txt …")

    retriever = KnowledgeRetriever(KNOWLEDGE_DB_DIR)
    print(f"Done — {len(retriever._chunks)} chunks indexed.")
    print(f"Cache written to: {cache_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
