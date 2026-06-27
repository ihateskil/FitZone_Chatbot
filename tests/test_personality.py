"""Tests for the Motivational Personality Modes."""

from src.personality import get_personality, get_personality_prompt, list_personalities, PersonalityMode


class TestPersonality:
    def test_coach_mode(self):
        p = get_personality("coach")
        assert p.mode == PersonalityMode.COACH

    def test_drill_sergeant_mode(self):
        p = get_personality("drill_sergeant")
        assert p.mode == PersonalityMode.DRILL_SERGEANT

    def test_science_professor_mode(self):
        p = get_personality("science_professor")
        assert p.mode == PersonalityMode.SCIENCE_PROFESSOR

    def test_zen_guide_mode(self):
        p = get_personality("zen_guide")
        assert p.mode == PersonalityMode.ZEN_GUIDE

    def test_invalid_falls_back_to_coach(self):
        p = get_personality("nonexistent")
        assert p.mode == PersonalityMode.COACH

    def test_prompt_has_content(self):
        prompt = get_personality_prompt("drill_sergeant")
        assert len(prompt) > 50

    def test_list_personalities(self):
        plist = list_personalities()
        assert len(plist) == 4
        modes = [p["mode"] for p in plist]
        assert "coach" in modes
        assert "drill_sergeant" in modes
