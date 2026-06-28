"""Per-session lift history storage for the Progressive Overload Tracker.

Stores logged lifts per session (identified by session_id) with date tracking.
Backed by JSON files in the .cache/sessions/ directory.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from src.config import CACHE_DIR
from src.lift_parser import ParsedLift, ParsedSet


SESSIONS_DIR = CACHE_DIR / "sessions"


class WorkoutSession:
    """A single workout session with logged lifts."""
    session_id: str
    date: str  # ISO format YYYY-MM-DD
    lifts: list[dict[str, Any]]
    rpe: float | None = None

    @staticmethod
    def now_iso() -> str:
        return date.today().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "date": self.date,
            "lifts": self.lifts,
            "rpe": self.rpe,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkoutSession":
        return cls(
            session_id=data["session_id"],
            date=data["date"],
            lifts=data.get("lifts", []),
            rpe=data.get("rpe"),
        )


def _lift_to_dict(lift: ParsedLift) -> dict[str, Any]:
    return {
        "exercise": lift.exercise,
        "sets": [{"weight": s.weight, "reps": s.reps} for s in lift.sets],
        "total_volume": lift.total_volume,
    }


class SessionStore:
    """Store and retrieve workout sessions per user/client."""

    def __init__(self, sessions_dir: Path = SESSIONS_DIR) -> None:
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
        return self.sessions_dir / f"{safe_id}.json"

    def _load_session(self, session_id: str) -> dict[str, Any] | None:
        path = self._session_path(session_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _save_session(self, session_id: str, data: dict[str, Any]) -> None:
        path = self._session_path(session_id)
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        fd, tmp_path = tempfile.mkstemp(dir=self.sessions_dir, suffix=".tmp")
        try:
            os.write(fd, payload)
        finally:
            os.close(fd)
        os.replace(tmp_path, path)

    def log_lifts(
        self,
        session_id: str,
        lifts: list[ParsedLift],
        rpe: float | None = None,
    ) -> dict[str, Any]:
        """Log lifts to a session. Creates session if it does not exist."""
        data = self._load_session(session_id)
        if data is None:
            data = {
                "session_id": session_id,
                "date": WorkoutSession.now_iso(),
                "lifts": [],
                "rpe": None,
            }

        for lift in lifts:
            data["lifts"].append(_lift_to_dict(lift))

        if rpe is not None:
            data["rpe"] = rpe

        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_session(session_id, data)
        return data

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve a session by ID."""
        return self._load_session(session_id)

    def get_exercise_history(
        self,
        session_id: str,
        exercise: str,
    ) -> list[dict[str, Any]]:
        """Get all logged entries for a specific exercise in a session."""
        data = self._load_session(session_id)
        if data is None:
            return []
        exercise_lower = exercise.lower()
        return [
            entry for entry in data.get("lifts", [])
            if str(entry.get("exercise", "")).lower() == exercise_lower
        ]

    def get_all_exercise_history(self, exercise: str) -> list[dict[str, Any]]:
        """Get all logged entries for an exercise across ALL sessions."""
        results: list[dict[str, Any]] = []
        exercise_lower = exercise.lower()
        for path in self.sessions_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            for entry in data.get("lifts", []):
                if str(entry.get("exercise", "")).lower() == exercise_lower:
                    entry["_session_date"] = data.get("date", "")
                    entry["_session_id"] = data.get("session_id", "")
                    results.append(entry)
        results.sort(key=lambda x: x.get("_session_date", ""), reverse=False)
        return results

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all sessions (lightweight: id + date + lift count)."""
        sessions = []
        for path in self.sessions_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            sessions.append({
                "session_id": data.get("session_id", ""),
                "date": data.get("date", ""),
                "lift_count": len(data.get("lifts", [])),
                "rpe": data.get("rpe"),
            })
        sessions.sort(key=lambda x: x.get("date", ""), reverse=True)
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if it existed."""
        path = self._session_path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False
