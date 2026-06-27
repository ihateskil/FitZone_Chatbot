"""Auto-progressor engine for the Progressive Overload Tracker.

Uses 1RM estimation formulas, volume load, IRV, and ACWR from
gym_calculations.txt to compute next-session recommendations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# 1RM Estimation Formulas
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OneRMResult:
    """Result of 1RM estimation."""
    estimated_1rm: float
    formula: str
    weight: float
    reps: int


def epley_1rm(weight: float, reps: int) -> float:
    """Epley formula: 1RM = W * (1 + R/30). Best for R <= 10."""
    return weight * (1 + reps / 30)


def brzycki_1rm(weight: float, reps: int) -> float:
    """Brzycki formula: 1RM = W / (1.0278 - 0.0278 * R). Accurate up to 10 reps."""
    if reps >= 36:
        return weight  # formula breaks down at high reps
    return weight / (1.0278 - 0.0278 * reps)


def lombardi_1rm(weight: float, reps: int) -> float:
    """Lombardi formula: 1RM = W * R^0.10."""
    return weight * (reps ** 0.10)


def oconner_1rm(weight: float, reps: int) -> float:
    """O'Conner formula: 1RM = W * (1 + 0.025 * R)."""
    return weight * (1 + 0.025 * reps)


def estimate_1rm(weight: float, reps: int) -> OneRMResult:
    """Estimate 1RM using the best formula for the rep range.

    Uses Brzycki for <= 10 reps (most accurate), Epley for 11-20,
    and returns the weight as-is for > 20 reps (too fatigued to estimate).
    """
    if reps <= 0 or weight <= 0:
        return OneRMResult(weight, "none", weight, reps)
    if reps == 1:
        return OneRMResult(weight, "exact", weight, reps)
    if reps <= 10:
        rm = brzycki_1rm(weight, reps)
        return OneRMResult(round(rm, 1), "brzycki", weight, reps)
    if reps <= 20:
        rm = epley_1rm(weight, reps)
        return OneRMResult(round(rm, 1), "epley", weight, reps)
    return OneRMResult(weight, "too_many_reps", weight, reps)


# ---------------------------------------------------------------------------
# Volume & Intensity Metrics
# ---------------------------------------------------------------------------

def volume_load(sets: list[dict[str, Any]]) -> float:
    """Total volume load = sum(weight * reps) for all sets."""
    return sum(s.get("weight", 0) * s.get("reps", 0) for s in sets)


def intensity_relative_volume(sets: list[dict[str, Any]], estimated_1rm: float) -> float:
    """IRV = sum(reps * %1RM) across sets. Optimal hypertrophy: 20-30."""
    if estimated_1rm <= 0:
        return 0.0
    return sum(s.get("reps", 0) * (s.get("weight", 0) / estimated_1rm) for s in sets)


# ---------------------------------------------------------------------------
# Brzycki Rep-Intensity Table
# ---------------------------------------------------------------------------

# Percentage of 1RM for a given number of reps (Brzycki)
_REP_INTENSITY = {
    1: 1.00, 2: 0.95, 3: 0.93, 4: 0.90, 5: 0.87,
    6: 0.85, 7: 0.83, 8: 0.80, 9: 0.77, 10: 0.75,
    11: 0.73, 12: 0.70, 13: 0.67, 14: 0.65, 15: 0.63,
}


def weight_for_reps(estimated_1rm: float, target_reps: int) -> float:
    """Calculate weight to use for a target rep count."""
    pct = _REP_INTENSITY.get(target_reps)
    if pct is None:
        # Extrapolate: roughly 2.5% drop per rep beyond 15
        pct = max(0.40, 0.63 - 0.025 * (target_reps - 15))
    return round(estimated_1rm * pct, 1)


# ---------------------------------------------------------------------------
# Progression Recommendation
# ---------------------------------------------------------------------------

@dataclass
class ProgressionRecommendation:
    """Next-session recommendation for an exercise."""
    exercise: str
    current_1rm: float
    recommended_weight: float
    recommended_reps: int
    recommended_sets: int
    reasoning: str
    irv: float
    irv_status: str  # "optimal", "low", "high"


def recommend_progression(
    exercise: str,
    last_sets: list[dict[str, Any]],
    goal: str = "hypertrophy",
) -> ProgressionRecommendation:
    """Generate next-session progression recommendation.

    Args:
        exercise: Exercise name
        last_sets: List of {weight, reps} dicts from last session
        goal: "hypertrophy", "strength", or "endurance"
    """
    if not last_sets:
        return ProgressionRecommendation(
            exercise=exercise, current_1rm=0, recommended_weight=0,
            recommended_reps=0, recommended_sets=0,
            reasoning="No previous data available.", irv=0, irv_status="low",
        )

    # Find the heaviest set for 1RM estimation
    heaviest = max(last_sets, key=lambda s: s.get("weight", 0))
    best_weight = heaviest.get("weight", 0)
    best_reps = heaviest.get("reps", 0)

    rm_result = estimate_1rm(best_weight, best_reps)
    current_1rm = rm_result.estimated_1rm

    # Calculate IRV
    irv = intensity_relative_volume(last_sets, current_1rm)

    # Determine IRV status
    if irv < 20:
        irv_status = "low"
    elif irv > 30:
        irv_status = "high"
    else:
        irv_status = "optimal"

    # Build recommendation based on goal and IRV
    n_sets = len(last_sets)

    if goal == "strength":
        target_reps = 5
        target_sets = max(n_sets, 3)
        increment = 2.5  # kg
    elif goal == "endurance":
        target_reps = 15
        target_sets = max(n_sets, 3)
        increment = 2.5
    else:  # hypertrophy
        target_reps = 8
        target_sets = max(n_sets, 3)
        increment = 2.5

    rec_weight = weight_for_reps(current_1rm, target_reps)

    # If IRV is low, we can push weight up
    # If IRV is high, maybe add reps instead or deload slightly
    reasoning_parts = []
    reasoning_parts.append(
        f"Estimated 1RM: {current_1rm} (via {rm_result.formula} from {best_weight}x{best_reps})"
    )
    reasoning_parts.append(f"IRV: {irv:.1f} ({irv_status})")

    if irv_status == "low":
        # Can afford to increase load
        rec_weight = round(rec_weight + increment, 1)
        reasoning_parts.append(
            f"IRV is below optimal range (20-30), so bumping weight by {increment} to increase stimulus."
        )
    elif irv_status == "high":
        # Volume is high, consider reducing
        rec_weight = round(rec_weight - increment, 1)
        reasoning_parts.append(
            f"IRV is above optimal range (20-30), reducing weight by {increment} to manage fatigue."
        )
    else:
        reasoning_parts.append(
            f"IRV is in optimal range. Maintaining load with small progression."
        )

    reasoning = " ".join(reasoning_parts)

    return ProgressionRecommendation(
        exercise=exercise,
        current_1rm=current_1rm,
        recommended_weight=max(rec_weight, 0),
        recommended_reps=target_reps,
        recommended_sets=target_sets,
        reasoning=reasoning,
        irv=round(irv, 1),
        irv_status=irv_status,
    )


# ---------------------------------------------------------------------------
# ACWR Calculator
# ---------------------------------------------------------------------------

def acute_chronic_workload_ratio(
    acute_volume: float,
    chronic_volume: float,
) -> float:
    """Calculate ACWR. Sweet spot: 0.8-1.3. Danger: > 1.5."""
    if chronic_volume <= 0:
        return 0.0
    return round(acute_volume / chronic_volume, 2)


def acwr_risk(acwr: float) -> str:
    """Interpret ACWR value."""
    if acwr < 0.8:
        return "undertrained"
    if acwr <= 1.3:
        return "optimal"
    if acwr <= 1.5:
        return "elevated"
    return "danger_zone"
