"""Retry helpers for external API calls."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from config import LLM_RETRY_ATTEMPTS, LLM_RETRY_DELAY_SEC
from logging_utils import logger

T = TypeVar("T")


def with_retries(
    fn: Callable[[], T],
    *,
    attempts: int = LLM_RETRY_ATTEMPTS,
    delay_sec: float = LLM_RETRY_DELAY_SEC,
    label: str = "operation",
) -> T:
    """Retry a callable with exponential backoff."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
            logger.warning("%s failed (attempt %s/%s): %s", label, attempt, attempts, exc)
            if attempt < attempts:
                time.sleep(delay_sec * attempt)
    raise RuntimeError(f"{label} failed after {attempts} attempts") from last_error
