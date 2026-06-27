"""Shared fixtures for FitZone test suite."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import src.api as api


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch):
    """Provide valid env vars so the FastAPI lifespan can start under TestClient."""
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("FITZONE_API_KEY", "test-fitzone-key-1234567890")
    monkeypatch.setattr(api, "GROQ_API_KEY", "test-groq-key")
    monkeypatch.setattr(api, "warmup_agent", lambda: object())


@pytest.fixture
def client(monkeypatch):
    """Return a TestClient with a mocked agent response."""
    monkeypatch.setattr(
        api,
        "run_agent_full",
        lambda message, history=None, science_mode=False, personality="coach": SimpleNamespace(
            text=f"Answer: {message}",
            latency_ms=12.3,
            blocked=False,
            block_reason=None,
            in_scope=True,
            lift_logged=False,
            progression_hint=None,
        ),
    )
    with TestClient(api.app) as c:
        yield c
