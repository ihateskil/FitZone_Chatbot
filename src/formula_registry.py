"""Formula registry and transparency mode for Show Your Work feature.

Provides structured formula definitions that can be referenced when
the LLM uses them, enabling transparent explanations of calculations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Formula:
    """A structured formula definition."""
    id: str
    name: str
    equation: str
    description: str
    inputs: list[str]
    conditions: str
    example: str


FORMULAS: dict[str, Formula] = {
    "mifflin_st_jeor_men": Formula(
        id="mifflin_st_jeor_men",
        name="Mifflin-St Jeor (Men)",
        equation="BMR = (10 x weight_kg) + (6.25 x height_cm) - (5 x age) + 5",
        description="Standard best practice BMR equation for men.",
        inputs=["weight_kg", "height_cm", "age"],
        conditions="Use when weight, height, and age are known but body fat % is not.",
        example="For 85kg, 180cm, 30yr: BMR = (10x85) + (6.25x180) - (5x30) + 5 = 1885 kcal",
    ),
    "mifflin_st_jeor_women": Formula(
        id="mifflin_st_jeor_women",
        name="Mifflin-St Jeor (Women)",
        equation="BMR = (10 x weight_kg) + (6.25 x height_cm) - (5 x age) - 161",
        description="Standard best practice BMR equation for women.",
        inputs=["weight_kg", "height_cm", "age"],
        conditions="Use when weight, height, and age are known but body fat % is not.",
        example="For 65kg, 165cm, 28yr: BMR = (10x65) + (6.25x165) - (5x28) - 161 = 1335 kcal",
    ),
    "katch_mcardle": Formula(
        id="katch_mcardle",
        name="Katch-McArdle",
        equation="BMR = 370 + (21.6 x LBM), where LBM = weight_kg x (1 - body_fat%/100)",
        description="Most accurate BMR equation when lean body mass is known.",
        inputs=["weight_kg", "body_fat_pct"],
        conditions="Use when body fat % is available. More accurate than Mifflin-St Jeor.",
        example="For 85kg at 15% BF: LBM=72.25, BMR = 370 + (21.6 x 72.25) = 1933 kcal",
    ),
    "harris_benedict_men": Formula(
        id="harris_benedict_men",
        name="Harris-Benedict Revised (Men)",
        equation="BMR = 88.362 + (13.397 x W) + (4.799 x H) - (5.677 x A)",
        description="Revised Harris-Benedict equation for men (Roza & Shizgal, 1984).",
        inputs=["weight_kg", "height_cm", "age"],
        conditions="Legacy equation, less accurate than Mifflin-St Jeor for modern populations.",
        example="For 85kg, 180cm, 30yr: BMR = 88.362 + 1138.745 + 863.82 - 170.31 = 1920 kcal",
    ),
    "tdee": Formula(
        id="tdee",
        name="Total Daily Energy Expenditure",
        equation="TDEE = BMR x Activity Multiplier",
        description="TDEE accounts for all daily energy expenditure including activity.",
        inputs=["bmr", "activity_multiplier"],
        conditions="Multipliers: Sedentary=1.2, Light=1.375, Moderate=1.55, Very=1.725, Extreme=1.9",
        example="BMR 1885 x 1.55 (moderately active) = 2922 kcal",
    ),
    "bmi": Formula(
        id="bmi",
        name="Body Mass Index",
        equation="BMI = weight_kg / (height_m x height_m)",
        description="Population-level body composition indicator.",
        inputs=["weight_kg", "height_m"],
        conditions="Not accurate for muscular individuals. Categories: <18.5 underweight, 18.5-24.9 normal, 25-29.9 overweight, >=30 obese.",
        example="85kg / (1.80 x 1.80) = 26.2 (overweight by BMI, but may be normal for muscular build)",
    ),
    "navy_body_fat_men": Formula(
        id="navy_body_fat_men",
        name="U.S. Navy Body Fat (Men)",
        equation="BF% = 495 / (1.0324 - 0.19077 x log10(waist-neck) + 0.15456 x log10(height)) - 450",
        description="Circumference-based body fat estimation for men.",
        inputs=["waist_cm", "neck_cm", "height_cm"],
        conditions="Reasonable estimate for most men. Less accurate at extreme leanness or obesity.",
        example="Waist 85cm, Neck 38cm, Height 180cm -> ~15.2%",
    ),
    "epley_1rm": Formula(
        id="epley_1rm",
        name="Epley 1RM",
        equation="1RM = Weight x (1 + Reps/30)",
        description="1-rep max estimation. Best for reps <= 10.",
        inputs=["weight", "reps"],
        conditions="Most accurate in the 1-10 rep range. Less accurate >15 reps.",
        example="185 x (1 + 8/30) = 234.3 lbs estimated 1RM",
    ),
    "brzycki_1rm": Formula(
        id="brzycki_1rm",
        name="Brzycki 1RM",
        equation="1RM = Weight / (1.0278 - 0.0278 x Reps)",
        description="Highly accurate 1RM estimation for up to 10 reps.",
        inputs=["weight", "reps"],
        conditions="Most accurate for 1-10 reps. Preferred over Epley for low rep ranges.",
        example="185 / (1.0278 - 0.0278 x 8) = 229.7 lbs estimated 1RM",
    ),
    "volume_load": Formula(
        id="volume_load",
        name="Volume Load (Tonnage)",
        equation="Volume = Sets x Reps x Weight",
        description="Total work performed. Key driver of hypertrophy and strength gains.",
        inputs=["sets", "reps", "weight"],
        conditions="Use to track total workload per exercise, session, or week.",
        example="3 x 8 x 185 = 4440 lbs total volume",
    ),
    "irv": Formula(
        id="irv",
        name="Intensity Relative Volume",
        equation="IRV = Sets x Reps x %1RM",
        description="Volume relative to 1RM. Optimal hypertrophy range: 20-30 per exercise.",
        inputs=["sets", "reps", "pct_1rm"],
        conditions="IRV < 20 = insufficient stimulus. IRV > 30 = excessive fatigue risk.",
        example="3 x 8 x 0.75 (75% 1RM) = 18 -> below optimal, consider more volume or load",
    ),
    "acwr": Formula(
        id="acwr",
        name="Acute:Chronic Workload Ratio",
        equation="ACWR = Acute Workload (7 days) / Chronic Workload (28-day avg)",
        description="Injury prevention metric tracking training load ramp rate.",
        inputs=["acute_volume", "chronic_volume"],
        conditions="Sweet spot: 0.8-1.3. Elevated: 1.3-1.5. Danger zone: >1.5 (high injury risk).",
        example="5000 / 4000 = 1.25 (optimal zone - safe progression)",
    ),
    "karvonen_thr": Formula(
        id="karvonen_thr",
        name="Karvonen Target Heart Rate",
        equation="THR = (HRR x %Intensity) + Resting HR, where HRR = Max HR - Resting HR",
        description="Heart rate reserve method for training zone calculation.",
        inputs=["max_hr", "resting_hr", "intensity_pct"],
        conditions="Zone 1: 50-60%, Zone 2: 60-70%, Zone 3: 70-80%, Zone 4: 80-90%, Zone 5: 90-100%",
        example="HRR=190-60=130, THR at 75% = (130x0.75)+60 = 157.5 bpm",
    ),
    "max_hr_fox": Formula(
        id="max_hr_fox",
        name="Max Heart Rate (Fox/Haskell)",
        equation="MHR = 220 - Age",
        description="Simple age-based maximum heart rate estimation.",
        inputs=["age"],
        conditions="Standard formula. Tanaka (208-0.7xAge) is more accurate for older adults.",
        example="220 - 30 = 190 bpm max",
    ),
}


def get_formula(formula_id: str) -> Formula | None:
    """Look up a formula by ID."""
    return FORMULAS.get(formula_id)


def search_formulas(query: str) -> list[Formula]:
    """Search formulas by keyword match in name, equation, or description."""
    query_lower = query.lower()
    results = []
    for f in FORMULAS.values():
        text = f"{f.name} {f.equation} {f.description}".lower()
        if any(word in text for word in query_lower.split()):
            results.append(f)
    return results


def format_formula_detail(formula: Formula) -> str:
    """Format a formula for display in science mode."""
    return (
        f"**{formula.name}**\n"
        f"Equation: `{formula.equation}`\n"
        f"Inputs: {', '.join(formula.inputs)}\n"
        f"When to use: {formula.conditions}\n"
        f"Example: {formula.example}"
    )


# System prompt addition for science mode
SCIENCE_MODE_PROMPT_ADDITION = """\

## Science Mode (Formula Transparency)
The user has enabled **Science Mode**. In this mode you MUST:
- Show your work on every calculation. State the formula name, the equation, plug in the numbers step by step, and give the result.
- When you choose one formula over another (e.g., Mifflin-St Jeor vs Katch-McArdle), explain WHY you chose it and what the alternative would have given.
- Use this format for calculations:
  **Formula:** [Name]
  **Equation:** `formula here`
  **Plugging in:** substitution with numbers
  **Result:** answer with units
  **Why this formula:** brief reason + what alternative would give
- For non-calculated answers, you can respond naturally but still cite principles/research when relevant.
"""

COACH_MODE_PROMPT_ADDITION = """\

## Coach Mode (Default)
You are in standard coaching mode. Respond naturally and conversationally like an expert coach. You don't need to show formulas or step-by-step math unless the user specifically asks. Just give clear, actionable, confident answers.
"""
