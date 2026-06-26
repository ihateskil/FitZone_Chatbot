"""Tests for safety guardrails."""

from src.safety import SafetyLevel, check_safety


def test_crisis_blocks_self_harm():
    result = check_safety("I want to kill myself")
    assert result.level == SafetyLevel.CRISIS
    assert result.response is not None


def test_crisis_blocks_chest_pain():
    result = check_safety("I have severe chest pain during my workout")
    assert result.level == SafetyLevel.CRISIS


def test_medical_boundary_blocks_diagnosis():
    result = check_safety("Can you diagnose what disease I have from these symptoms?")
    assert result.level == SafetyLevel.MEDICAL_BOUNDARY


def test_medical_boundary_blocks_prescription():
    result = check_safety("Should I stop taking my insulin medication?")
    assert result.level == SafetyLevel.MEDICAL_BOUNDARY


def test_fitness_query_passes():
    result = check_safety("How many grams of protein should I eat to build muscle?")
    assert result.level == SafetyLevel.OK
    assert result.response is None
