"""Tests for the ACWR Recovery Engine."""

import tempfile
from pathlib import Path

from src.lift_parser import LiftParser
from src.session_store import SessionStore
from src.recovery import compute_weekly_volumes, assess_recovery, recovery_context_for_agent


class TestRecovery:
    def test_weekly_volumes_computed(self, tmp_path):
        store = SessionStore(sessions_dir=tmp_path)
        lifts = LiftParser.parse("bench 185x8 185x6 190x5")
        store.log_lifts("test", lifts)
        volumes = compute_weekly_volumes(store, "test")
        assert len(volumes) == 5

    def test_assess_recovery_returns_status(self, tmp_path):
        store = SessionStore(sessions_dir=tmp_path)
        lifts = LiftParser.parse("bench 185x8 185x6 190x5")
        store.log_lifts("test", lifts)
        volumes = compute_weekly_volumes(store, "test")
        status = assess_recovery(volumes)
        assert status.risk_level in ("undertrained", "optimal", "elevated", "danger_zone")

    def test_empty_recovery(self):
        status = assess_recovery([])
        assert status.risk_level == "undertrained"

    def test_recovery_context_generated(self, tmp_path):
        store = SessionStore(sessions_dir=tmp_path)
        lifts = LiftParser.parse("bench 185x8 185x6 190x5")
        store.log_lifts("test", lifts)
        ctx = recovery_context_for_agent(store, "test")
        assert ctx is not None
        assert "RECOVERY" in ctx
