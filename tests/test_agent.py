"""Tests for intent router heuristics."""

from src.fitness_agent import IntentRouter, _sanitize_reference_context


def test_out_of_scope_heuristic():
    assert IntentRouter.heuristic_classify("Write me Python code for weather") == "OUT_OF_SCOPE"


def test_in_scope_heuristic():
    assert IntentRouter.heuristic_classify("How many calories in chicken breast?") == "IN_SCOPE"


def test_sanitize_strips_source_tags():
    raw = "[Source: gym_calculations.txt | relevance: 0.320]\nBMR formula here"
    cleaned = _sanitize_reference_context(raw)
    assert "[Source:" not in cleaned
    assert "BMR formula" in cleaned
