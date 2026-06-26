"""Structured logging for FitZone agent operations."""

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from src.config import LOG_DIR

_LOG_CONFIGURED = False


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure application logging once."""
    global _LOG_CONFIGURED
    logger = logging.getLogger("fitzone")
    if _LOG_CONFIGURED:
        return logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(LOG_DIR / "fitzone.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    logger.propagate = False
    _LOG_CONFIGURED = True
    return logger


def log_event(event: str, **fields: Any) -> None:
    """Emit a structured JSON log line."""
    logger = setup_logging()
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    logger.info(json.dumps(payload, default=str))


@contextmanager
def timed_operation(operation: str, **fields: Any) -> Iterator[dict[str, float]]:
    """Context manager that logs operation duration."""
    logger = setup_logging()
    start = time.perf_counter()
    timing: dict[str, float] = {}
    try:
        yield timing
    finally:
        timing["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": operation,
            **fields,
            **timing,
        }
        logger.info(json.dumps(payload, default=str))
