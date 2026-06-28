"""
Weekly training tracker — aggregates session data into weekly summaries
and computes trends (volume, strength, recovery) over time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from src.progressor import estimate_1rm, volume_load, acute_chronic_workload_ratio, acwr_risk
from src.session_store import SessionStore


@dataclass
class ExerciseWeeklySummary:
    exercise: str
    total_volume: float
    session_count: int
    best_set_weight: float
    best_set_reps: int
    estimated_1rm: float
    total_sets: int


@dataclass
class WeeklySummary:
    week_start: str
    total_volume: float
    session_count: int
    exercise_summaries: list[ExerciseWeeklySummary]
    avg_rpe: float | None = None


@dataclass
class TrendData:
    volume_trend: str
    strength_trends: dict[str, str]
    acwr: float
    acwr_risk: str
    weekly_summaries: list[WeeklySummary]


def _get_week_start(d: date) -> str:
    return (d - timedelta(days=d.weekday())).isoformat()


def _parse_date(date_str: str) -> date | None:
    try:
        return date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def compute_weekly_summaries(
    store: SessionStore,
    weeks: int = 5,
) -> list[WeeklySummary]:
    """Compute weekly summaries from all session data."""
    sessions = store.list_sessions()
    if not sessions:
        return []

    today = date.today()
    weekly_data: dict[str, dict[str, Any]] = {}

    for sess in sessions:
        sess_date = _parse_date(sess.get("date", ""))
        if sess_date is None:
            continue
        # Only look at recent weeks
        if sess_date < today - timedelta(weeks=weeks):
            continue

        week_key = _get_week_start(sess_date)
        sess_full = store.get_session(sess.get("session_id", ""))
        if sess_full is None:
            continue

        lifts = sess_full.get("lifts", [])
        if week_key not in weekly_data:
            weekly_data[week_key] = {
                "total_volume": 0.0,
                "session_count": 0,
                "rpes": [],
                "exercises": {},
            }

        wd = weekly_data[week_key]
        wd["session_count"] += 1
        if sess_full.get("rpe") is not None:
            wd["rpes"].append(sess_full["rpe"])

        for lift in lifts:
            sets = lift.get("sets", [])
            vol = volume_load(sets)
            wd["total_volume"] += vol
            ex_name = lift.get("exercise", "Unknown")
            if ex_name not in wd["exercises"]:
                wd["exercises"][ex_name] = {
                    "total_volume": 0.0,
                    "session_count": 0,
                    "all_sets": [],
                }
            ex = wd["exercises"][ex_name]
            ex["total_volume"] += vol
            ex["session_count"] += 1
            ex["all_sets"].extend(sets)

    result: list[WeeklySummary] = []
    for i in range(weeks):
        week_d = today - timedelta(weeks=weeks - 1 - i)
        ws = _get_week_start(week_d)
        if ws not in weekly_data:
            result.append(WeeklySummary(
                week_start=ws, total_volume=0.0, session_count=0,
                exercise_summaries=[], avg_rpe=None,
            ))
            continue

        wd = weekly_data[ws]
        ex_summaries = []
        for ex_name, ex_data in wd["exercises"].items():
            all_sets = ex_data["all_sets"]
            best = max(all_sets, key=lambda s: s.get("weight", 0) * s.get("reps", 0)) if all_sets else {"weight": 0, "reps": 0}
            rm_result = estimate_1rm(best.get("weight", 0), best.get("reps", 0))
            ex_summaries.append(ExerciseWeeklySummary(
                exercise=ex_name,
                total_volume=round(ex_data["total_volume"], 1),
                session_count=ex_data["session_count"],
                best_set_weight=best.get("weight", 0),
                best_set_reps=best.get("reps", 0),
                estimated_1rm=round(rm_result.estimated_1rm, 1),
                total_sets=len(all_sets),
            ))

        avg_rpe = round(sum(wd["rpes"]) / len(wd["rpes"]), 1) if wd["rpes"] else None

        result.append(WeeklySummary(
            week_start=ws,
            total_volume=round(wd["total_volume"], 1),
            session_count=wd["session_count"],
            exercise_summaries=sorted(ex_summaries, key=lambda x: -x.total_volume),
            avg_rpe=avg_rpe,
        ))

    return result


def compute_trends(weekly: list[WeeklySummary]) -> TrendData:
    """Compute volume trend, strength trends, and ACWR from weekly summaries."""
    if not weekly:
        return TrendData(
            volume_trend="insufficient_data", strength_trends={},
            acwr=0.0, acwr_risk="undertrained",
            weekly_summaries=[],
        )

    recent = weekly[-1].total_volume
    if len(weekly) >= 4:
        chronic_weeks = weekly[-4:-1]
        chronic = sum(w.total_volume for w in chronic_weeks) / len(chronic_weeks)
    elif len(weekly) >= 2:
        chronic_weeks = weekly[:-1]
        chronic = sum(w.total_volume for w in chronic_weeks) / len(chronic_weeks)
    else:
        chronic = recent

    acwr = acute_chronic_workload_ratio(recent, chronic)
    risk = acwr_risk(acwr)

    # Volume trend: compare last 3 weeks
    if len(weekly) >= 3:
        recent_weeks = weekly[-3:]
        vols = [w.total_volume for w in recent_weeks]
        if vols[2] > vols[1] * 1.05 and vols[1] > vols[0] * 1.05:
            volume_trend = "increasing"
        elif vols[2] < vols[0] * 0.95:
            volume_trend = "decreasing"
        else:
            volume_trend = "stable"
    else:
        volume_trend = "insufficient_data"

    # Strength trends per exercise (compare latest estimated 1RM)
    strength_trends: dict[str, str] = {}
    if len(weekly) >= 2:
        current_exercises = {ex.exercise: ex for ex in weekly[-1].exercise_summaries if ex.estimated_1rm > 0}
        prev_exercises = {ex.exercise: ex for ex in weekly[-2].exercise_summaries if ex.estimated_1rm > 0}
        for ex_name, curr in current_exercises.items():
            prev = prev_exercises.get(ex_name)
            if prev and prev.estimated_1rm > 0:
                change = ((curr.estimated_1rm - prev.estimated_1rm) / prev.estimated_1rm) * 100
                if change > 2:
                    strength_trends[ex_name] = "gaining"
                elif change < -2:
                    strength_trends[ex_name] = "declining"
                else:
                    strength_trends[ex_name] = "stable"

    return TrendData(
        volume_trend=volume_trend,
        strength_trends=strength_trends,
        acwr=round(acwr, 2),
        acwr_risk=risk,
        weekly_summaries=weekly,
    )


def format_trend_context(trend: TrendData) -> str:
    """Format trend data for LLM context injection."""
    weeks = trend.weekly_summaries
    if not weeks:
        return ""

    lines = ["## Weekly Training Trends"]
    lines.append(f"Volume trend (3-week): {trend.volume_trend.replace('_', ' ')}")
    lines.append(f"ACWR: {trend.acwr} ({trend.acwr_risk.replace('_', ' ')})")

    if weeks[-1].session_count > 0:
        last = weeks[-1]
        lines.append(f"")
        lines.append(f"### Current Week ({last.week_start})")
        lines.append(f"Sessions: {last.session_count}")
        lines.append(f"Total volume: {last.total_volume:,.0f}")
        if last.avg_rpe:
            lines.append(f"Avg RPE: {last.avg_rpe}")
        if last.exercise_summaries:
            lines.append(f"Exercises tracked: {len(last.exercise_summaries)}")

    if trend.strength_trends:
        lines.append(f"")
        lines.append(f"### Strength Trends (week-over-week)")
        for ex, trend_dir in sorted(trend.strength_trends.items()):
            emoji = "+" if trend_dir == "gaining" else "-" if trend_dir == "declining" else "="
            lines.append(f"  {ex}: {emoji} {trend_dir}")

    # Multi-week volume table
    if len(weeks) >= 2:
        lines.append(f"")
        lines.append(f"### Volume History")
        for w in weeks[-5:]:
            vol_str = f"{w.total_volume:>8,.0f}" if w.total_volume > 0 else "   —   "
            lines.append(f"  {w.week_start}  {vol_str}  ({w.session_count} sessions)")

    return "\n".join(lines)
