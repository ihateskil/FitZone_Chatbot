"""Tests for the lift parser module."""

from src.lift_parser import LiftParser, ParsedSet, ParsedLift, is_lift_log


class TestLiftParser:
    def test_bench_with_spaces(self):
        results = LiftParser.parse("bench 185x8 185x6 190x5")
        assert len(results) == 1
        r = results[0]
        assert r.exercise == "bench press"
        assert r.set_count == 3
        assert r.sets[0] == ParsedSet(weight=185.0, reps=8)
        assert r.sets[1] == ParsedSet(weight=185.0, reps=6)
        assert r.sets[2] == ParsedSet(weight=190.0, reps=5)

    def test_squat_with_colon_and_commas(self):
        results = LiftParser.parse("squat: 225x5, 225x5, 225x5")
        assert len(results) == 1
        r = results[0]
        assert r.exercise == "squat"
        assert r.set_count == 3

    def test_sets_reps_at_weight(self):
        results = LiftParser.parse("5x5 at 225 on bench press")
        r = results[0]
        assert r.exercise == "bench press"
        assert r.set_count == 5
        assert r.sets[0].weight == 225.0

    def test_verb_prefix(self):
        results = LiftParser.parse("I deadlifted 315x3, 325x2, 335x1")
        r = results[0]
        assert r.exercise == "deadlift"
        assert r.max_weight == 335.0

    def test_ohp_alias(self):
        results = LiftParser.parse("OHP 95x8 95x8 95x7")
        r = results[0]
        assert r.exercise == "overhead press"
        assert r.set_count == 3

    def test_rdl_alias(self):
        results = LiftParser.parse("rdl 185x10 185x10 185x8")
        r = results[0]
        assert r.exercise == "romanian deadlift"

    def test_empty_input(self):
        assert LiftParser.parse("") == []

    def test_pyramid_sets(self):
        results = LiftParser.parse("bench: 135x10, 185x8, 225x5, 275x3")
        assert len(results) == 1
        r = results[0]
        assert r.exercise == "bench press"
        assert r.set_count == 4

    def test_volume_calculation(self):
        results = LiftParser.parse("bench 185x8 185x6 190x5")
        r = results[0]
        assert r.total_volume == 185*8 + 185*6 + 190*5

    def test_max_weight_and_reps(self):
        results = LiftParser.parse("bench 185x8 185x6 190x5")
        r = results[0]
        assert r.max_weight == 190.0
        assert r.max_reps == 8


class TestIsLiftLog:
    def test_lift_detected(self):
        assert is_lift_log("bench 185x8 185x6 190x5")
        assert is_lift_log("squat: 225x5")

    def test_non_lift_not_detected(self):
        assert not is_lift_log("What is my BMR?")
        assert not is_lift_log("How many calories in chicken?")
