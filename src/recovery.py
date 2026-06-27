"""ACWR Fatigue & Recovery Engine.

Tracks weekly training volume, computes ACWR, and provides
recovery recommendations based on fatigue accumulation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from src.progressor import acute_chronic_workload_ratio, acwr_risk, volume_load
from src.session_store import SessionStore


@dataclass(frozen=True)
class WeeklyVolume:
    """Training volume for a single week."""
    week_start: str  # ISO date
    total_volume: float
    session_count: int
    exercises: dict[str, float]  # exercise -> volume


@dataclass
class RecoveryStatus:
    """Current recovery and fatigue status."""
    acute_volume: float
    chronic_volume: float
    acwr: float
    risk_level: str  # undertrained, optimal, elevated, danger_zone
    recommendation: str
    deload_recommended: bool
    weekly_breakdown: list[WeeklyVolume]


def compute_weekly_volumes(
    store: SessionStore,
    session_id: str = "default",
    weeks: int = 5,
) -> list[WeeklyVolume]:
    """Compute training volume per week from session history.

    Returns volumes for the last N weeks, oldest first.
    """
    session = store.get_session(session_id)
    if session is None:
        return []

    today = date.today()
    weekly: dict[str, dict[str, Any]] = {}

    # For simplicity: single session -> single week
    # In a full implementation, you'd iterate over multiple sessions
    session_date = session.get("date", today.isoformat())
    lifts = session.get("lifts", [])

    # Compute total volume and per-exercise volume
    total_vol = 0.0
    exercise_vols: dict[str, float] = {}
    for lift in lifts:
        sets = lift.get("sets", [])
        vol = volume_load(sets)
        total_vol += vol
        exercise = lift.get("exercise", "Unknown")
        exercise_vols[exercise] = exercise_vols.get(exercise, 0) + vol

    # Determine week start (Monday)
    try:
        d = date.fromisoformat(session_date)
    except ValueError:
        d = today
    week_start = (d - timedelta(days=d.weekday())).isoformat()

    weekly[week_start] = {
        "total_volume": total_vol,
        "session_count": 1,
        "exercises": exercise_vols,
    }

    # Build result list for requested weeks
    result: list[WeeklyVolume] = []
    for i in range(weeks):
        week_d = today - timedelta(weeks=weeks - 1 - i)
        ws = (week_d - timedelta(days=week_d.weekday())).isoformat()
        data = weekly.get(ws, {"total_volume": 0.0, "session_count": 0, "exercises": {}})
        result.append(WeeklyVolume(
            week_start=ws,
            total_volume=data["total_volume"],
            session_count=data["session_count"],
            exercises=data.get("exercises", {}),
        ))

    return result


def assess_recovery(
    weekly_volumes: list[WeeklyVolume],
) -> RecoveryStatus:
    """Assess recovery status from weekly volume data.

    Requires at least 5 weeks of data for full ACWR calculation.
    Can work with less (uses available data).
    """
    if not weekly_volumes:
        return RecoveryStatus(
            acute_volume=0, chronic_volume=0, acwr=0,
            risk_level="undertrained",
            recommendation="No training data available. Start logging your workouts!",
            deload_recommended=False,
            weekly_breakdown=[],
        )

    # Acute = most recent week (last in list)
    acute = weekly_volumes[-1].total_volume

    # Chronic = average of previous 4 weeks (or however many we have)
    if len(weekly_volumes) > 1:
        chronic_weeks = weekly_volumes[:-1]
        chronic = sum(w.total_volume for w in chronic_weeks) / len(chronic_weeks)
    else:
        chronic = acute  # Can't compute ratio with 1 week

    acwr = acute_chronic_workload_ratio(acute, chronic)
    risk = acwr_risk(acwr)

    # Build recommendation
    if risk == "danger_zone":
        rec = (
            f"ACWR is {acwr} (DANGER ZONE). Your training load spiked significantly. "
            f"Recommend a deload week: reduce volume by 40-60% and intensity by 10-15%. "
            f"This prevents overuse injuries and allows supercompensation."
        )
        deload = True
    elif risk == "elevated":
        rec = (
            f"ACWR is {acwr} (elevated). You're ramping up load faster than optimal. "
            f"Consider a light deload or maintaining current volume for 1-2 weeks "
            f"before increasing further."
        )
        deload = False
    elif risk == "optimal":
        rec = (
            f"ACWR is {acwr} (optimal). Your training load progression is well-managed. "
            f"Continue with planned progression."
        )
        deload = False
    else:  # undertrained
        rec = (
            f"ACWR is {acwr} (undertrained). Your current volume is below your chronic average. "
            f"This is normal after a deload or rest. Start ramping back up gradually."
        )
        deload = False

    return RecoveryStatus(
        acute_volume=round(acute, 1),
        chronic_volume=round(chronic, 1),
        acwr=acwr,
        risk_level=risk,
        recommendation=rec,
        deload_recommended=deload,
        weekly_breakdown=weekly_volumes,
    )


def recovery_context_for_agent(
    store: SessionStore,
    session_id: str = "default",
) -> str | None:
    """Build recovery context string for agent injection.

    Returns None if no sessions exist.
    """
    session = store.get_session(session_id)
    if session is None or not session.get("lifts"):
        return None

    weekly = compute_weekly_volumes(store, session_id)
    status = assess_recovery(weekly)

    return (
        f"[RECOVERY & FATIGUE STATUS]\n"
        f"ACWR: {status.acwr} ({status.risk_level})\n"
        f"Acute load (this week): {status.acute_volume}\n"
        f"Chronic load (4-week avg): {status.chronic_volume}\n"
        f"Deload recommended: {'YES' if status.deload_recommended else 'No'}\n"
        f"Recommendation: {status.recommendation}"
    )
