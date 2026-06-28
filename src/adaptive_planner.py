"""
Adaptive planner — generates personalized nutrition and training
recommendations based on user profile and weekly trends.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.user_profile import UserProfile
from src.weekly_tracker import TrendData, WeeklySummary


@dataclass
class NutritionAdjustment:
    category: str
    current_value: str
    recommended_value: str
    reasoning: str


@dataclass
class TrainingAdjustment:
    category: str
    current_value: str
    recommended_value: str
    reasoning: str


@dataclass
class AdaptiveRecommendations:
    nutrition: list[NutritionAdjustment]
    training: list[TrainingAdjustment]
    deload_recommended: bool
    summary: str

    def format_for_context(self) -> str:
        if not self.nutrition and not self.training:
            return ""
        lines = ["## Adaptive Recommendations"]
        if self.summary:
            lines.append(self.summary)
        if self.nutrition:
            lines.append("")
            lines.append("### Nutrition Adjustments")
            for adj in self.nutrition:
                lines.append(f"  {adj.category}: {adj.recommended_value}")
                lines.append(f"    → {adj.reasoning}")
        if self.training:
            lines.append("")
            lines.append("### Training Adjustments")
            for adj in self.training:
                lines.append(f"  {adj.category}: {adj.recommended_value}")
                lines.append(f"    → {adj.reasoning}")
        return "\n".join(lines)


class AdaptivePlanner:
    """Analyzes user profile + weekly trends to generate adaptive recommendations."""

    @staticmethod
    def analyze(
        profile: UserProfile,
        trend: TrendData,
    ) -> AdaptiveRecommendations:
        nutrition_adjs: list[NutritionAdjustment] = []
        training_adjs: list[TrainingAdjustment] = []

        # --- Nutrition adjustments based on goal + weight change progress ---
        if profile.primary_goal in ("cutting", "lose weight", "fat_loss"):
            if profile.weight_kg:
                goal = profile.primary_goal
                nutrition_adjs.append(NutritionAdjustment(
                    category="Calorie target",
                    current_value="per profile",
                    recommended_value="TDEE minus 300-500 kcal",
                    reasoning=f"Goal is {goal}. Maintain a moderate deficit to lose 0.5-1 lb per week "
                              f"while preserving muscle mass. Prioritize protein (2.0-2.4g/kg).",
                ))
        elif profile.primary_goal in ("bulking", "build muscle", "muscle_gain"):
            nutrition_adjs.append(NutritionAdjustment(
                category="Calorie target",
                current_value="per profile",
                recommended_value="TDEE plus 200-400 kcal",
                reasoning=f"Goal is muscle gain. A slight surplus maximizes anabolic response "
                          f"while minimizing fat gain. Protein at 1.6-2.2g/kg.",
            ))
        elif profile.primary_goal in ("maintain", "recomp"):
            nutrition_adjs.append(NutritionAdjustment(
                category="Calorie target",
                current_value="per profile",
                recommended_value="Around maintenance (TDEE)",
                reasoning=f"Maintenance or recomp phase. Keep protein high (1.6-2.2g/kg) "
                          f"and adjust carbs around training days.",
            ))

        # --- Protein adjustment based on experience/goal ---
        if profile.primary_goal in ("cutting", "lose weight", "fat_loss"):
            nutrition_adjs.append(NutritionAdjustment(
                category="Protein intake",
                current_value="standard recommendation",
                recommended_value="2.0-2.4 g/kg body weight",
                reasoning="Higher protein during a cut preserves lean mass and increases satiety.",
            ))
        elif profile.experience_level in ("beginner", "novice"):
            nutrition_adjs.append(NutritionAdjustment(
                category="Protein intake",
                current_value="standard recommendation",
                recommended_value="1.6-2.0 g/kg body weight",
                reasoning="Adequate protein supports beginners' rapid adaptation phase.",
            ))

        # --- Hydration based on activity ---
        if profile.training_frequency and profile.training_frequency >= 5:
            nutrition_adjs.append(NutritionAdjustment(
                category="Hydration",
                current_value="standard 2-3L/day",
                recommended_value="3-4L/day plus electrolytes",
                reasoning=f"Training {profile.training_frequency}x/week increases fluid losses. "
                          f"Add electrolytes (sodium, potassium, magnesium) on training days.",
            ))

        # --- Training volume adjustment based on ACWR ---
        if trend.acwr_risk == "danger_zone":
            training_adjs.append(TrainingAdjustment(
                category="Training volume",
                current_value=f"Current ACWR: {trend.acwr}",
                recommended_value="Reduce by 40-60% (deload week)",
                reasoning="ACWR is in the danger zone (>1.5). High injury risk from load spike. "
                          "Deload this week to allow tissue repair and supercompensation.",
            ))
        elif trend.acwr_risk == "elevated":
            training_adjs.append(TrainingAdjustment(
                category="Training volume",
                current_value=f"Current ACWR: {trend.acwr}",
                recommended_value="Maintain or reduce slightly (0-10%)",
                reasoning="ACWR is elevated (1.3-1.5). Hold volume steady this week "
                          "to let the chronic average catch up before increasing further.",
            ))
        elif trend.acwr_risk == "undertrained" and len(trend.weekly_summaries) >= 3:
            training_adjs.append(TrainingAdjustment(
                category="Training volume",
                current_value=f"Current ACWR: {trend.acwr}",
                recommended_value="Increase by 5-10%",
                reasoning="ACWR is below 0.8 — you're underloading relative to your history. "
                          "Gradually increase volume to avoid detraining.",
            ))

        # --- Frequency adjustment ---
        if trend.weekly_summaries:
            last_week = trend.weekly_summaries[-1]
            if profile.training_frequency and last_week.session_count > 0:
                if last_week.session_count < profile.training_frequency * 0.7:
                    training_adjs.append(TrainingAdjustment(
                        category="Session frequency",
                        current_value=f"{last_week.session_count} sessions/week",
                        recommended_value=f"Aim for {profile.training_frequency} sessions/week",
                        reasoning=f"You averaged {last_week.session_count} sessions but your target is "
                                  f"{profile.training_frequency}. Try shorter sessions if time is the constraint.",
                    ))

        # --- Volume trend adjustment ---
        if trend.volume_trend == "decreasing" and trend.acwr_risk not in ("danger_zone", "elevated"):
            training_adjs.append(TrainingAdjustment(
                category="Volume trend",
                current_value="Decreasing over last 3 weeks",
                recommended_value="Assess cause — fatigue or life stress?",
                reasoning="Volume has been dropping. If fatigued, consider a deload. "
                          "If life stress, maintain intensity but reduce volume temporarily.",
            ))

        # --- Strength trend adjustment ---
        declining_strength = [ex for ex, s in trend.strength_trends.items() if s == "declining"]
        if declining_strength:
            for ex in declining_strength[:2]:
                training_adjs.append(TrainingAdjustment(
                    category=f"Strength ({ex})",
                    current_value="Declining week-over-week",
                    recommended_value="Reduce intensity or change exercise variation",
                    reasoning=f"Estimated 1RM on {ex} is dropping. This may indicate fatigue, "
                              f"technique breakdown, or insufficient recovery. Try a 5-10% intensity "
                              f"reduction or swap to a variation for 2-4 weeks.",
                ))

        # --- Sleep/recovery adjustment ---
        if profile.sleep_hours and profile.sleep_hours < 6:
            training_adjs.append(TrainingAdjustment(
                category="Recovery capacity",
                current_value=f"{profile.sleep_hours} hrs sleep/night",
                recommended_value="Target 7-9 hrs sleep",
                reasoning="Sleep under 6 hours significantly impairs muscle recovery, "
                          "hormone production, and performance. Prioritize sleep hygiene "
                          "and consider reducing training volume until sleep improves.",
            ))

        # --- Short summary ---
        summary_parts = []
        if training_adjs:
            summary_parts.append(f"{len(training_adjs)} training adjustment(s) suggested.")
        if nutrition_adjs:
            summary_parts.append(f"{len(nutrition_adjs)} nutrition adjustment(s) suggested.")
        deload = any("deload" in adj.recommended_value.lower() for adj in training_adjs)

        return AdaptiveRecommendations(
            nutrition=nutrition_adjs,
            training=training_adjs,
            deload_recommended=deload,
            summary=" ".join(summary_parts) if summary_parts else "All metrics look good — continue current plan.",
        )
