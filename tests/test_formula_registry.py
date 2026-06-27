"""Tests for the Formula Registry."""

from src.formula_registry import get_formula, search_formulas, format_formula_detail, FORMULAS


class TestFormulaRegistry:
    def test_get_formula(self):
        f = get_formula("mifflin_st_jeor_men")
        assert f is not None
        assert f.name == "Mifflin-St Jeor (Men)"

    def test_search_bmr(self):
        results = search_formulas("BMR")
        assert len(results) >= 3

    def test_format_detail(self):
        f = get_formula("brzycki_1rm")
        detail = format_formula_detail(f)
        assert "Brzycki" in detail
        assert "Equation" in detail

    def test_formula_count(self):
        assert len(FORMULAS) >= 10

    def test_acwr_formula_exists(self):
        f = get_formula("acwr")
        assert f is not None
        assert "0.8-1.3" in f.conditions
