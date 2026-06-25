"""Tests for the Render-ready FitZone API."""

from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

import api


def test_health_reports_ready(monkeypatch):
    monkeypatch.setattr(api, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(api, "warmup_agent", lambda: object())

    with TestClient(api.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_requires_api_key(monkeypatch):
    monkeypatch.setattr(api, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(api, "warmup_agent", lambda: object())
    monkeypatch.delenv("FITZONE_API_KEY", raising=False)

    with TestClient(api.app) as client:
        response = client.post("/v1/chat", json={"message": "How many calories in chicken?"})

    assert response.status_code == 500


def test_chat_returns_response(monkeypatch):
    monkeypatch.setattr(api, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(api, "warmup_agent", lambda: object())
    monkeypatch.setenv("FITZONE_API_KEY", "secret")
    monkeypatch.setattr(
        api,
        "run_agent_full",
        lambda message, history=None: SimpleNamespace(
            text=f"Answer: {message}",
            latency_ms=12.3,
            blocked=False,
            block_reason=None,
            in_scope=True,
        ),
    )

    with TestClient(api.app) as client:
        response = client.post(
            "/v1/chat",
            headers={"X-API-Key": "secret"},
            json={"message": "How many calories in chicken?"},
        )

    assert response.status_code == 200
    assert response.json()["response"] == "Answer: How many calories in chicken?"
    assert response.json()["blocked"] is False
