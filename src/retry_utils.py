"""Retry helpers for external API calls."""

from __future__ import annotations

import http.client
import logging
import socket
import time
import urllib.error
from collections.abc import Callable
from typing import TypeVar

from src.config import LLM_RETRY_ATTEMPTS, LLM_RETRY_DELAY_SEC
from src.logging_utils import setup_logging

T = TypeVar("T")

# Transient exceptions worth retrying — NOT programming errors like TypeError.
RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
    urllib.error.URLError,
    http.client.RemoteDisconnected,
    socket.timeout,
)


def with_retries(
    fn: Callable[[], T],
    *,
    attempts: int = LLM_RETRY_ATTEMPTS,
    delay_sec: float = LLM_RETRY_DELAY_SEC,
    label: str = "operation",
) -> T:
    """Retry a callable with linear backoff on transient errors only."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except RETRYABLE_EXCEPTIONS as exc:
            last_error = exc
            logging.getLogger("fitzone").warning("%s failed (attempt %s/%s): %s", label, attempt, attempts, exc)
            if attempt < attempts:
                time.sleep(delay_sec * attempt)
    raise RuntimeError(f"{label} failed after {attempts} attempts") from last_error
