"""Tests for intent router and context sanitization."""

from src.fitness_agent import _sanitize_reference_context
from src.intent_router import IntentRouter


def test_out_of_scope_heuristic():
    router = IntentRouter()
    assert router.classify_scope("Write me Python code for weather") is False


def test_in_scope_heuristic():
    router = IntentRouter()
    assert router.classify_scope("How many calories in chicken breast?") is True


def test_sanitize_strips_source_tags():
    raw = "[Source: gym_calculations.txt | relevance: 0.320]\nBMR formula here"
    cleaned = _sanitize_reference_context(raw)
    assert "[Source:" not in cleaned
    assert "BMR formula" in cleaned
