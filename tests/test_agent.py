"""Tests for intent router and context sanitization."""

from src.fitness_agent import _sanitize_reference_context
from src.intent_router import IntentRouter


def test_out_of_scope_heuristic():
    router = IntentRouter()
    assert router.classify_scope("Write me Python code for a website") is False


def test_in_scope_heuristic():
    router = IntentRouter()
    assert router.classify_scope("How many calories in chicken breast?") is True


def test_health_condition_in_scope():
    router = IntentRouter()
    assert router.classify_scope("i have a heart condition") is True
    assert router.classify_scope("my knees hurt when i squat") is True
    assert router.classify_scope("i have diabetes can i still build muscle") is True


def test_recipe_in_scope():
    router = IntentRouter()
    assert router.classify_scope("whats a good recipe for protein pancakes") is True
    assert router.classify_scope("healthy chicken recipe") is True


def test_travel_weather_in_scope():
    router = IntentRouter()
    assert router.classify_scope("i travel for work how do i stay fit") is True
    assert router.classify_scope("can i run in cold weather") is True
    assert router.classify_scope("best app for tracking macros") is True


def test_sanitize_strips_source_tags():
    raw = "[Source: gym_calculations.txt | relevance: 0.320]\nBMR formula here"
    cleaned = _sanitize_reference_context(raw)
    assert "[Source:" not in cleaned
    assert "BMR formula" in cleaned
