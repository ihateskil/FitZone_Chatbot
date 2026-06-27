"""
Formula Calculator for FitZone.
Provides a FormulaCalculator class that takes a formula name + user inputs
and returns a computed result + explanation string for the LLM to use.

Formulas are defined in knowledge/formulas.json and include BMR, TDEE,
1RM estimators, macro targets, body fat %, ACWR, heart rate zones,
volume load, and IRV.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from src.config import BASE_DIR

FORMULAS_JSON = BASE_DIR / "knowledge" / "formulas.json"


class FormulaResult:
    """Result of a formula calculation."""

    def __init__(
        self,
        formula_name: str,
        formula_id: str,
        inputs: dict[str, float | str],
        result: float | dict[str, float],
        unit: str,
        explanation: str,
    ) -> None:
        self.formula_name = formula_name
        self.formula_id = formula_id
        self.inputs = inputs
        self.result = result
        self.unit = unit
        self.explanation = explanation

    def to_science_mode_string(self) -> str:
        """Format for science mode display."""
        lines = [f"**Formula:** {self.formula_name}"]
        lines.append(f"**Equation:** `{self.explanation}`")
        lines.append(f"**Plugging in:** {self._format_inputs()}")
        if isinstance(self.result, dict):
            for key, val in self.result.items():
                lines.append(f"**{key.replace("_", " ").title()}:** {val} {self.unit}")
        else:
            lines.append(f"**Result:** {self.result} {self.unit}")
        return "\n".join(lines)

    def _format_inputs(self) -> str:
        parts = []
        for key, val in self.inputs.items():
            parts.append(f"{key}={val}")
        return ", ".join(parts)


class FormulaCalculator:
    """
    Calculator for fitness/nutrition formulas.
    Loads formulas from knowledge/formulas.json and computes results.
    """

    _instance: FormulaCalculator | None = None

    def __new__(cls) -> FormulaCalculator:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._formulas: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not FORMULAS_JSON.exists():
            return
        self._formulas = json.loads(FORMULAS_JSON.read_text(encoding="utf-8"))

    def list_formulas(self) -> list[dict[str, str]]:
        """List all available formulas."""
        return [
            {"id": fid, "name": fdata["name"], "category": fdata["category"]}
            for fid, fdata in self._formulas.items()
        ]

    def get_formula_info(self, formula_id: str) -> dict[str, Any] | None:
        """Get formula metadata without computing."""
        return self._formulas.get(formula_id)

    def calculate(self, formula_id: str, **kwargs: Any) -> FormulaResult | None:
        """
        Calculate a formula result.

        Args:
            formula_id: The formula identifier (e.g., "bmr_mifflin_st_jeor_men")
            **kwargs: Input values matching the formula's inputs

        Returns:
            FormulaResult with computed result and explanation, or None if formula not found.
        """
        formula = self._formulas.get(formula_id)
        if formula is None:
            return None

        # Special handling for formulas with complex compute logic
        if formula_id == "macro_calorie_targets":
            return self._calc_calorie_targets(formula, **kwargs)
        if formula_id == "macro_protein_target":
            return self._calc_protein_target(formula, **kwargs)
        if formula_id == "body_fat_navy_men":
            return self._calc_body_fat_navy_men(formula, **kwargs)
        if formula_id == "body_fat_navy_women":
            return self._calc_body_fat_navy_women(formula, **kwargs)

        # Generic lambda-based computation
        compute_str = formula.get("compute", "")
        try:
            compute_fn = eval(compute_str)
            result = compute_fn(**kwargs)
            if result is None:
                return None
        except Exception:
            return None

        example = formula.get("example", {})
        unit = formula.get("example", {}).get("unit", "")

        return FormulaResult(
            formula_name=formula["name"],
            formula_id=formula_id,
            inputs=kwargs,
            result=result,
            unit=unit,
            explanation=formula["formula"],
        )

    def _calc_calorie_targets(self, formula: dict, **kwargs) -> FormulaResult:
        """Special handler for calorie targets by goal."""
        tdee = kwargs.get("tdee", 0)
        goal = kwargs.get("goal", "maintain")

        multipliers = {"fat_loss": -500, "maintain": 0, "muscle_gain": 300}
        result = tdee + multipliers.get(goal, 0)

        goal_names = {"fat_loss": "Fat Loss", "maintain": "Maintenance", "muscle_gain": "Muscle Gain"}
        goal_name = goal_names.get(goal, goal)

        return FormulaResult(
            formula_name=formula["name"],
            formula_id="macro_calorie_targets",
            inputs=kwargs,
            result=result,
            unit="kcal",
            explanation=f"TDEE ({tdee} kcal) + {multipliers.get(goal, 0)} kcal adjustment for {goal_name} = {result} kcal",
        )

    def _calc_protein_target(self, formula: dict, **kwargs) -> FormulaResult:
        """Special handler for protein target."""
        weight_kg = kwargs.get("weight_kg", 0)
        goal = kwargs.get("goal", "muscle_building")

        multipliers = {
            "general_health": 0.8,
            "endurance": 1.3,
            "muscle_building": 2.0,
            "cutting": 2.2,
        }
        multiplier = multipliers.get(goal, 1.6)
        result = round(weight_kg * multiplier, 0)

        return FormulaResult(
            formula_name=formula["name"],
            formula_id="macro_protein_target",
            inputs=kwargs,
            result=result,
            unit="g",
            explanation=f"{weight_kg} kg x {multiplier}g/kg ({goal.replace("_", " ")}) = {result}g protein per day",
        )

    def _calc_body_fat_navy_men(self, formula: dict, **kwargs) -> FormulaResult:
        """Navy body fat formula for men."""
        waist = kwargs.get("waist_cm", 0)
        neck = kwargs.get("neck_cm", 0)
        height = kwargs.get("height_cm", 0)
        if waist - neck <= 0:
            return None
        result = round(
            495 / (1.0324 - 0.19077 * math.log10(waist - neck) + 0.15456 * math.log10(height)) - 450,
            1
        )
        return FormulaResult(
            formula_name=formula["name"],
            formula_id="body_fat_navy_men",
            inputs=kwargs,
            result=result,
            unit="%",
            explanation=f"495 / (1.0324 - 0.19077 * log10({waist}-{neck}) + 0.15456 * log10({height})) - 450",
        )

    def _calc_body_fat_navy_women(self, formula: dict, **kwargs) -> FormulaResult:
        """Navy body fat formula for women."""
        waist = kwargs.get("waist_cm", 0)
        hip = kwargs.get("hip_cm", 0)
        neck = kwargs.get("neck_cm", 0)
        height = kwargs.get("height_cm", 0)
        if waist + hip - neck <= 0:
            return None
        result = round(
            495 / (1.29579 - 0.35004 * math.log10(waist + hip - neck) + 0.22100 * math.log10(height)) - 450,
            1
        )
        return FormulaResult(
            formula_name=formula["name"],
            formula_id="body_fat_navy_women",
            inputs=kwargs,
            result=result,
            unit="%",
            explanation=f"495 / (1.29579 - 0.35004 * log10({waist}+{hip}-{neck}) + 0.22100 * log10({height})) - 450",
        )

    def search(self, query: str) -> list[dict[str, str]]:
        """Search formulas by keyword."""
        query_lower = query.lower()
        results = []
        for fid, fdata in self._formulas.items():
            text = f"{fdata["name"]} {fdata["category"]} {fdata["description"]}".lower()
            if any(word in text for word in query_lower.split()):
                results.append({"id": fid, "name": fdata["name"], "category": fdata["category"]})
        return results


def get_formula_calculator() -> FormulaCalculator:
    """Get the singleton FormulaCalculator instance."""
    return FormulaCalculator()
