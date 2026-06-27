"""Tests for the progressor engine module."""

from src.progressor import (
    estimate_1rm, epley_1rm, brzycki_1rm,
    volume_load, intensity_relative_volume, weight_for_reps,
    recommend_progression, acute_chronic_workload_ratio, acwr_risk,
)


class TestOneRM:
    def test_exact_1rm(self):
        r = estimate_1rm(225, 1)
        assert r.estimated_1rm == 225
        assert r.formula == "exact"

    def test_brzycki_range(self):
        r = estimate_1rm(185, 8)
        assert r.formula == "brzycki"
        assert r.estimated_1rm > 185

    def test_epley_range(self):
        r = estimate_1rm(135, 12)
        assert r.formula == "epley"
        assert r.estimated_1rm > 135

    def test_too_many_reps(self):
        r = estimate_1rm(100, 25)
        assert r.formula == "too_many_reps"

    def test_zero_reps(self):
        r = estimate_1rm(100, 0)
        assert r.estimated_1rm == 100


class TestVolumeMetrics:
    def test_volume_load(self):
        sets = [{"weight": 185, "reps": 8}, {"weight": 185, "reps": 6}, {"weight": 190, "reps": 5}]
        assert volume_load(sets) == 185*8 + 185*6 + 190*5

    def test_irv_positive(self):
        sets = [{"weight": 185, "reps": 8}, {"weight": 185, "reps": 6}, {"weight": 190, "reps": 5}]
        rm = estimate_1rm(185, 8).estimated_1rm
        assert intensity_relative_volume(sets, rm) > 0


class TestWeightForReps:
    def test_five_reps(self):
        w = weight_for_reps(225, 5)
        assert abs(w - 225 * 0.87) < 1


class TestProgression:
    def test_recommendation_with_data(self):
        sets = [{"weight": 185, "reps": 8}, {"weight": 185, "reps": 6}, {"weight": 190, "reps": 5}]
        rec = recommend_progression("bench press", sets, goal="hypertrophy")
        assert rec.exercise == "bench press"
        assert rec.current_1rm > 0
        assert rec.recommended_weight > 0
        assert rec.irv_status in ("low", "optimal", "high")

    def test_empty_data(self):
        rec = recommend_progression("squat", [])
        assert rec.current_1rm == 0


class TestACWR:
    def test_optimal(self):
        assert acwr_risk(acute_chronic_workload_ratio(5000, 4000)) == "optimal"

    def test_danger_zone(self):
        assert acwr_risk(acute_chronic_workload_ratio(8000, 4000)) == "danger_zone"

    def test_undertrained(self):
        assert acwr_risk(acute_chronic_workload_ratio(2000, 4000)) == "undertrained"

    def test_elevated(self):
        assert acwr_risk(acute_chronic_workload_ratio(5500, 4000)) == "elevated"

    def test_zero_chronic(self):
        assert acute_chronic_workload_ratio(5000, 0) == 0.0
