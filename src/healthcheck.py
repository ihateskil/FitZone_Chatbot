#!/usr/bin/env python3
"""Verify FitZone Chatbot environment and dependencies.

Provides two levels of checks:
  -Cheap: env vars + filesystem only (used by /health endpoint)
  - Expensive: full agent warmup with Groq call (used by /ready)
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # project root
sys.path.insert(0, str(BASE_DIR))  # add project root to path

from src.config import CACHE_DIR, GROQ_API_KEY, KNOWLEDGE_DB_DIR  # noqa: E402


def cheap_check() -> tuple[list[str], list[str]]:
    """Fast checks: env vars + filesystem. No network calls."""
    errors: list[str] = []
    warnings: list[str] = []

    if not GROQ_API_KEY:
        errors.append("GROQ_API_KEY is not set in .env")

    if not KNOWLEDGE_DB_DIR.is_dir():
        errors.append(f"Knowledge_db folder missing: {KNOWLEDGE_DB_DIR}")
    else:
        pdf_count = len(list(KNOWLEDGE_DB_DIR.glob("*.pdf")))
        gym_file = KNOWLEDGE_DB_DIR / "gym_calculations.txt"
        if pdf_count == 0 and not gym_file.exists():
            errors.append("Knowledge_db has no PDFs and no gym_calculations.txt")
        else:
            print(f"Knowledge_db: {pdf_count} PDFs, gym_calculations={'yes' if gym_file.exists() else 'no'}")

    cache_file = CACHE_DIR / "knowledge_chunks.json"
    if cache_file.exists():
        print(f"Knowledge cache: OK ({cache_file})")
    else:
        warnings.append("Knowledge cache not built — first request will be slow. Run: python scripts/rebuild_knowledge.py")

    return errors, warnings


def expensive_check() -> tuple[list[str], list[str]]:
    """Slow checks: full agent warmup including Groq LLM call."""
    errors: list[str] = []
    warnings: list[str] = []

    try:
        from src.fitness_agent import warmup_agent

        agent = warmup_agent()
        print(f"Agent loaded: {len(agent._knowledge._chunks)} knowledge chunks")
    except Exception as exc:
        errors.append(f"Agent failed to load: {exc}")

    return errors, warnings


def main() -> int:
    errors, warnings = cheap_check()

    if "--deep" in sys.argv:
        deep_errors, deep_warnings = expensive_check()
        errors.extend(deep_errors)
        warnings.extend(deep_warnings)

    for warning in warnings:
        print(f"WARNING: {warning}")

    if errors:
        print("\nHealth check FAILED:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("\nHealth check PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
