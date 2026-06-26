"""Tests for the Render-ready FitZone API."""

from __future__ import annotations

from fastapi.testclient import TestClient

import src.api as api


def test_health_reports_ready(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_requires_api_key(client, monkeypatch):
    # Valid startup key (set by conftest), but request carries no X-API-Key header.
    response = client.post("/v1/chat", json={"message": "How many calories in chicken?"})

    assert response.status_code == 401


def test_chat_returns_response(client):
    response = client.post(
        "/v1/chat",
        headers={"X-API-Key": "test-fitzone-key-1234567890"},
        json={"message": "How many calories in chicken?"},
    )

    assert response.status_code == 200
    assert response.json()["response"] == "Answer: How many calories in chicken?"
    assert response.json()["blocked"] is False


def test_chat_rejects_invalid_history_length(client):
    """History exceeding max_length=20 should be rejected by validation."""
    long_history = [{"role": "user", "content": "hi"}] * 25

    response = client.post(
        "/v1/chat",
        headers={"X-API-Key": "test-fitzone-key-1234567890"},
        json={"message": "How many calories in chicken?", "history": long_history},
    )

    assert response.status_code == 422


def test_chat_stream_returns_stream(client, monkeypatch):
    """Streaming endpoint should return 200 with text/event-stream content type."""
    monkeypatch.setattr(
        api,
        "stream_agent",
        lambda message, history=None: iter(["chunk1", "chunk2"]),
    )

    response = client.post(
        "/v1/chat/stream",
        headers={"X-API-Key": "test-fitzone-key-1234567890"},
        json={"message": "How many calories in chicken?"},
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    assert response.content == b"chunk1chunk2"
