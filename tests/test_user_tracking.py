"""Tests for user profile, weekly tracking, and adaptive planning modules."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

from src.user_profile import (
    ProfileStore,
    UserProfile,
    extract_profile_from_text,
    merge_profile,
)
from src.weekly_tracker import (
    WeeklySummary,
    ExerciseWeeklySummary,
    compute_weekly_summaries,
    compute_trends,
    format_trend_context,
    TrendData,
)
from src.adaptive_planner import AdaptivePlanner, NutritionAdjustment, TrainingAdjustment
from src.session_store import SessionStore
from src.lift_parser import LiftParser


@pytest.fixture
def tmp_session_store():
    """SessionStore backed by a temp directory (avoids tmp_path permission issues)."""
    d = tempfile.mkdtemp()
    store = SessionStore(sessions_dir=Path(d))
    yield store
    for p in Path(d).glob("*"):
        try:
            p.unlink()
        except OSError:
            pass
    try:
        os.rmdir(d)
    except OSError:
        pass


def _inject_session(store: SessionStore, session_id: str, date_str: str, lifts_text: str):
    """Helper: write a session directly into the store's JSON directory."""
    lifts = LiftParser.parse(lifts_text)
    lifts_dicts = []
    for lift in lifts:
        lifts_dicts.append({
            "exercise": lift.exercise,
            "sets": [{"weight": s.weight, "reps": s.reps} for s in lift.sets],
        })
    data = {
        "session_id": session_id,
        "date": date_str,
        "user_id": "test",
        "lifts": lifts_dicts,
    }
    path = store.sessions_dir / f"{session_id}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class TestUserProfile:
    def test_extract_weight_kg(self):
        result = extract_profile_from_text("I weigh 82 kg")
        assert result["weight_kg"] == 82.0

    def test_extract_weight_lbs(self):
        result = extract_profile_from_text("I weigh 180 lbs")
        assert abs(result["weight_kg"] - 81.6) < 0.2

    def test_extract_height_cm(self):
        result = extract_profile_from_text("I'm 180 cm")
        assert result["height_cm"] == 180

    def test_extract_height_ft(self):
        result = extract_profile_from_text("I'm 5'10")
        assert result["height_cm"] == 178

    def test_extract_age(self):
        result = extract_profile_from_text("I'm 25 years old")
        assert result["age"] == 25

    def test_extract_gender(self):
        result = extract_profile_from_text("I'm a male")
        assert result["gender"] == "male"

    def test_extract_body_fat(self):
        result = extract_profile_from_text("I'm 15% body fat")
        assert result["body_fat_pct"] == 15.0

    def test_extract_goal_bulking(self):
        result = extract_profile_from_text("I'm bulking right now")
        assert result["primary_goal"] == "bulking"

    def test_extract_experience(self):
        result = extract_profile_from_text("I'm a beginner")
        assert result["experience_level"] == "beginner"

    def test_extract_sleep(self):
        result = extract_profile_from_text("I get 7 hours of sleep")
        assert result["sleep_hours"] == 7.0

    def test_extract_frequency(self):
        result = extract_profile_from_text("I train 4x per week")
        assert result["training_frequency"] == 4

    def test_extract_injury(self):
        result = extract_profile_from_text("I injured my knee")
        assert "knee" in result.get("injuries", [])

    def test_extract_equipment(self):
        result = extract_profile_from_text("I have a home gym")
        assert "home gym" in result.get("equipment_available", [])

    def test_merge_profile_preserves_existing(self):
        current = {"user_id": "test", "weight_kg": 80.0, "injuries": ["shoulder"]}
        updates = {"weight_kg": 82.0, "age": 30}
        merged = merge_profile(current, updates)
        assert merged["weight_kg"] == 82.0
        assert merged["injuries"] == ["shoulder"]

    def test_merge_profile_accumulates_injuries(self):
        current = {"user_id": "test", "injuries": ["knee"]}
        updates = {"injuries": ["shoulder"]}
        merged = merge_profile(current, updates)
        assert "knee" in merged["injuries"]
        assert "shoulder" in merged["injuries"]

    def test_profile_store_save_load(self):
        d = Path(tempfile.mkdtemp())
        try:
            store = ProfileStore(profiles_dir=d)
            profile = UserProfile(user_id="test-user", weight_kg=85.0, age=30)
            store.save(profile)
            loaded = store.load("test-user")
            assert loaded.weight_kg == 85.0
            assert loaded.age == 30
        finally:
            for p in d.glob("*"):
                try: p.unlink()
                except OSError: pass
            try: os.rmdir(d)
            except OSError: pass

    def test_profile_store_update_from_conversation(self):
        d = Path(tempfile.mkdtemp())
        try:
            store = ProfileStore(profiles_dir=d)
            profile = store.update_from_conversation("test", "I weigh 82 kg and I'm 25 years old")
            assert profile.weight_kg == 82.0
            assert profile.age == 25
        finally:
            for p in d.glob("*"):
                try: p.unlink()
                except OSError: pass
            try: os.rmdir(d)
            except OSError: pass

    def test_profile_store_load_nonexistent(self):
        d = Path(tempfile.mkdtemp())
        try:
            store = ProfileStore(profiles_dir=d)
            profile = store.load("nonexistent")
            assert profile.user_id == "nonexistent"
        finally:
            for p in d.glob("*"):
                try: p.unlink()
                except OSError: pass
            try: os.rmdir(d)
            except OSError: pass

    def test_format_for_context_with_metrics(self):
        profile = UserProfile(user_id="test", weight_kg=82.0, height_cm=180,
                              age=30, primary_goal="cutting", experience_level="intermediate")
        ctx = profile.format_for_context()
        assert "Weight:" in ctx
        assert "Goal:" in ctx
        assert "Cutting" in ctx

    def test_format_for_context_empty(self):
        profile = UserProfile(user_id="test")
        assert profile.format_for_context() == ""


class TestWeeklyTracker:
    def test_no_sessions_returns_empty(self, tmp_session_store):
        assert compute_weekly_summaries(tmp_session_store) == []

    def test_single_session_aggregates(self, tmp_session_store):
        lifts = LiftParser.parse("bench 185x8 185x6 190x5")
        tmp_session_store.log_lifts("s1", lifts)
        summaries = compute_weekly_summaries(tmp_session_store)
        assert len(summaries) == 5
        assert summaries[-1].session_count == 1
        assert summaries[-1].total_volume > 0

    def test_multiple_sessions_same_week_merged(self, tmp_session_store):
        _inject_session(tmp_session_store, "s1", date.today().isoformat(), "bench 185x8")
        _inject_session(tmp_session_store, "s2", date.today().isoformat(), "squat 225x5")
        summaries = compute_weekly_summaries(tmp_session_store)
        current_week = summaries[-1]
        assert current_week.session_count == 2
        exercises = {e.exercise for e in current_week.exercise_summaries}
        assert "bench press" in exercises
        assert "squat" in exercises

    def test_volume_trend_insufficient_data(self):
        trend = compute_trends([])
        assert trend.volume_trend == "insufficient_data"

    def test_volume_trend_stable(self):
        weeks = [
            WeeklySummary(week_start="2026-06-01", total_volume=10000, session_count=3,
                          exercise_summaries=[]),
            WeeklySummary(week_start="2026-06-08", total_volume=10200, session_count=3,
                          exercise_summaries=[]),
            WeeklySummary(week_start="2026-06-15", total_volume=10100, session_count=3,
                          exercise_summaries=[]),
        ]
        trend = compute_trends(weeks)
        assert trend.volume_trend == "stable"

    def test_volume_trend_increasing(self):
        weeks = [
            WeeklySummary(week_start="2026-06-01", total_volume=10000, session_count=3,
                          exercise_summaries=[]),
            WeeklySummary(week_start="2026-06-08", total_volume=11000, session_count=3,
                          exercise_summaries=[]),
            WeeklySummary(week_start="2026-06-15", total_volume=12500, session_count=3,
                          exercise_summaries=[]),
        ]
        trend = compute_trends(weeks)
        assert trend.volume_trend == "increasing"

    def test_volume_trend_decreasing(self):
        weeks = [
            WeeklySummary(week_start="2026-06-01", total_volume=12000, session_count=3,
                          exercise_summaries=[]),
            WeeklySummary(week_start="2026-06-08", total_volume=10000, session_count=3,
                          exercise_summaries=[]),
            WeeklySummary(week_start="2026-06-15", total_volume=8000, session_count=3,
                          exercise_summaries=[]),
        ]
        trend = compute_trends(weeks)
        assert trend.volume_trend == "decreasing"

    def test_acwr_computed(self):
        weeks = [
            WeeklySummary(week_start="2026-05-01", total_volume=8000, session_count=3,
                          exercise_summaries=[]),
            WeeklySummary(week_start="2026-05-08", total_volume=8200, session_count=3,
                          exercise_summaries=[]),
            WeeklySummary(week_start="2026-05-15", total_volume=8100, session_count=3,
                          exercise_summaries=[]),
            WeeklySummary(week_start="2026-05-22", total_volume=8300, session_count=3,
                          exercise_summaries=[]),
            WeeklySummary(week_start="2026-05-29", total_volume=8400, session_count=3,
                          exercise_summaries=[]),
        ]
        trend = compute_trends(weeks)
        assert 0.5 < trend.acwr < 2.0
        assert trend.acwr_risk in ("undertrained", "optimal", "elevated", "danger_zone")

    def test_format_trend_context_includes_header(self):
        weeks = [
            WeeklySummary(week_start="2026-06-01", total_volume=10000, session_count=3,
                          exercise_summaries=[]),
            WeeklySummary(week_start="2026-06-08", total_volume=10200, session_count=3,
                          exercise_summaries=[]),
        ]
        trend = compute_trends(weeks)
        ctx = format_trend_context(trend)
        assert "Weekly Training Trends" in ctx
        assert "volume history" in ctx.lower()

    def test_format_trend_context_empty(self):
        assert format_trend_context(TrendData(volume_trend="", strength_trends={}, acwr=0, acwr_risk="", weekly_summaries=[])) == ""

    def test_strength_trend_detected(self, tmp_session_store):
        today_s = date.today().isoformat()
        last_week_s = (date.today() - timedelta(days=10)).isoformat()
        _inject_session(tmp_session_store, "old", last_week_s, "bench 200x5")
        _inject_session(tmp_session_store, "cur", today_s, "bench 210x5")
        summaries = compute_weekly_summaries(tmp_session_store)
        trend = compute_trends(summaries)
        ex = trend.strength_trends.get("bench press")
        assert ex is not None


class TestAdaptivePlanner:
    def test_cutting_nutrition_advice(self):
        profile = UserProfile(user_id="test", weight_kg=80, primary_goal="cutting")
        trend = TrendData(volume_trend="stable", strength_trends={}, acwr=1.0, acwr_risk="optimal",
                          weekly_summaries=[])
        rec = AdaptivePlanner.analyze(profile, trend)
        assert len(rec.nutrition) > 0
        cats = [a.category for a in rec.nutrition]
        assert "Calorie target" in cats

    def test_bulking_nutrition_advice(self):
        profile = UserProfile(user_id="test", weight_kg=80, primary_goal="bulking")
        trend = TrendData(volume_trend="stable", strength_trends={}, acwr=1.0, acwr_risk="optimal",
                          weekly_summaries=[])
        rec = AdaptivePlanner.analyze(profile, trend)
        cats = [a.category for a in rec.nutrition]
        assert "Calorie target" in cats

    def test_danger_zone_training_advice(self):
        profile = UserProfile(user_id="test")
        trend = TrendData(volume_trend="stable", strength_trends={}, acwr=1.6, acwr_risk="danger_zone",
                          weekly_summaries=[])
        rec = AdaptivePlanner.analyze(profile, trend)
        assert len(rec.training) > 0
        assert rec.deload_recommended
        cats = [a.category for a in rec.training]
        assert "Training volume" in cats

    def test_elevated_acwr_advice(self):
        profile = UserProfile(user_id="test")
        trend = TrendData(volume_trend="stable", strength_trends={}, acwr=1.4, acwr_risk="elevated",
                          weekly_summaries=[])
        rec = AdaptivePlanner.analyze(profile, trend)
        assert len(rec.training) > 0

    def test_sleep_deficit_advice(self):
        profile = UserProfile(user_id="test", sleep_hours=5.0)
        trend = TrendData(volume_trend="stable", strength_trends={}, acwr=1.0, acwr_risk="optimal",
                          weekly_summaries=[])
        rec = AdaptivePlanner.analyze(profile, trend)
        cats = [a.category for a in rec.training]
        assert "Recovery capacity" in cats

    def test_no_recommendations_for_minimal_data(self):
        profile = UserProfile(user_id="test")
        trend = TrendData(volume_trend="stable", strength_trends={}, acwr=1.0, acwr_risk="optimal",
                          weekly_summaries=[])
        rec = AdaptivePlanner.analyze(profile, trend)
        assert len(rec.nutrition) == 0

    def test_format_for_context_empty(self):
        rec = AdaptivePlanner.analyze(UserProfile(user_id="test"), compute_trends([]))
        assert isinstance(rec.format_for_context(), str)

    def test_format_for_context_contains_data(self):
        profile = UserProfile(user_id="test", weight_kg=80, primary_goal="cutting")
        trend = TrendData(volume_trend="stable", strength_trends={}, acwr=1.6, acwr_risk="danger_zone",
                          weekly_summaries=[])
        rec = AdaptivePlanner.analyze(profile, trend)
        ctx = rec.format_for_context()
        assert "Adaptive Recommendations" in ctx
        assert "Training volume" in ctx
        assert "Calorie target" in ctx
