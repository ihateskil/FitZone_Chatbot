"""Natural-language parser for workout lift logs.

Handles patterns like:
  - I benched 185x8, 185x6, 190x5
  - squatted 225 for 5x5
  - deadlift: 315x3, 325x2
  - OHP 95x8 95x8 95x7
  - did 3 sets of 10 at 135 on bench press
  - 5x5 at 225 on bench
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Exercise name normalization
# ---------------------------------------------------------------------------

_EXERCISE_ALIASES: dict[str, list[str]] = {
    "bench press": ["bench", "bench press", "flat bench", "bb bench", "barbell bench", "bp"],
    "squat": ["squat", "squats", "back squat", "bb squat", "barbell squat", "sq"],
    "deadlift": ["deadlift", "deadlifts", "dl", "conventional deadlift", "barbell deadlift"],
    "overhead press": ["ohp", "overhead press", "overhead", "military press", "press", "strict press", "standing press"],
    "barbell row": ["barbell row", "bb row", "bent over row", "bent-over row", "row", "pendlay row"],
    "pull-up": ["pull-up", "pull ups", "pullups", "pull up", "chin up", "chin-up"],
    "lat pulldown": ["lat pulldown", "lat pull down", "cable pulldown"],
    "leg press": ["leg press"],
    "leg curl": ["leg curl", "hamstring curl"],
    "leg extension": ["leg extension", "leg ext"],
    "bicep curl": ["bicep curl", "bicep", "curls", "bb curl", "barbell curl"],
    "tricep pushdown": ["tricep pushdown", "tricep", "pushdown", "cable pushdown"],
    "lateral raise": ["lateral raise", "side raise", "lat raise", "db lateral"],
    "chest fly": ["chest fly", "fly", "flye", "pec deck", "cable fly"],
    "incline bench press": ["incline bench", "incline press", "incline bench press", "inc bench"],
    "front squat": ["front squat", "front sq"],
    "romanian deadlift": ["rdl", "romanian deadlift", "romanian dl", "stiff leg deadlift"],
    "hack squat": ["hack squat"],
    "dip": ["dip", "dips"],
}

_ALIAS_MAP: dict[str, str] = {}
for _canonical, _aliases in _EXERCISE_ALIASES.items():
    for _alias in _aliases:
        _ALIAS_MAP[_alias] = _canonical


def _normalize_exercise(name: str) -> str:
    key = name.strip().lower()
    if key in _ALIAS_MAP:
        return _ALIAS_MAP[key]
    for alias, canonical in _ALIAS_MAP.items():
        if alias in key or key in alias:
            return canonical
    return name.strip().title()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ParsedSet:
    weight: float
    reps: int


@dataclass
class ParsedLift:
    exercise: str
    sets: list[ParsedSet] = field(default_factory=list)
    raw_text: str = ""

    @property
    def total_volume(self) -> float:
        return sum(s.weight * s.reps for s in self.sets)

    @property
    def max_weight(self) -> float:
        return max((s.weight for s in self.sets), default=0.0)

    @property
    def max_reps(self) -> int:
        return max((s.reps for s in self.sets), default=0)

    @property
    def set_count(self) -> int:
        return len(self.sets)


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# weight x reps  (e.g., 185x8, 225x3)
_WXR_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*x\s*(\d+)")

# N sets x reps at weight  (e.g., 5x5 at 225, 3 sets of 10 at 135)
_SXRXW_PATTERN = re.compile(
    r"(\d+)\s*(?:sets?\s*)?(?:x|of)\s*(\d+)\s+(?:at|@)\s+(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

_EXERCISE_KEYWORDS = frozenset(_ALIAS_MAP.keys())

_VERB_MAP = {
    "benched": "bench press", "squatted": "squat", "deadlifted": "deadlift",
    "pressed": "overhead press", "rowed": "barbell row", "curled": "bicep curl",
    "lifted": "deadlift",
}


# ---------------------------------------------------------------------------
# Exercise name extraction
# ---------------------------------------------------------------------------

def _extract_exercise_name(chunk: str) -> tuple[str, str]:
    chunk_lower = chunk.lower()
    sorted_aliases = sorted(_EXERCISE_KEYWORDS, key=len, reverse=True)
    for alias in sorted_aliases:
        if chunk_lower.startswith(alias):
            end = len(alias)
            remainder = chunk[end:].lstrip(" :-")
            return _ALIAS_MAP[alias], remainder

    for verb, exercise in _VERB_MAP.items():
        pattern = re.compile(rf"i\s+{verb}\s+(.*)", re.IGNORECASE)
        m = pattern.match(chunk)
        if m:
            return exercise, m.group(1)

    m = re.match(r"([\w\s]{2,25}?)\s*[:\-]\s+", chunk)
    if m:
        candidate = m.group(1).strip().lower()
        if candidate and not candidate[0].isdigit():
            return m.group(1).strip(), chunk[m.end():]

    return "", chunk


def _try_extract_trailing_exercise(text: str) -> str:
    m = re.search(r"(?:on|for)\s+([\w\s]{2,25})", text, re.IGNORECASE)
    if m:
        candidate = m.group(1).strip().lower()
        # Try longest alias matches first to avoid "press" matching before "bench press"
        sorted_aliases = sorted(_EXERCISE_KEYWORDS, key=len, reverse=True)
        for alias in sorted_aliases:
            if candidate.startswith(alias) or candidate == alias:
                return _ALIAS_MAP[alias]
        # Substring fallback (shorter aliases)
        for alias in sorted_aliases:
            if alias in candidate:
                return _ALIAS_MAP[alias]
        return candidate.title()
    return ""


# ---------------------------------------------------------------------------
# Core parsing
# ---------------------------------------------------------------------------

def _looks_like_sets_reps(text: str, wxr_matches: list) -> bool:
    """Check if WXR matches look like 'sets x reps at weight' instead of 'weight x reps'."""
    # If the text contains 'at' or '@' after the first match, this is likely sets x reps at weight
    for m in wxr_matches:
        after = text[m.end():].strip()
        if after.startswith(("at ", "@ ")):
            return True
    # If all matched "weights" are small (<=12) and consistent, likely sets x reps
    if wxr_matches:
        weights = [float(m.group(1)) for m in wxr_matches]
        if all(w <= 12 for w in weights):
            return True
    return False


def _parse_single_chunk(chunk: str) -> ParsedLift | None:
    exercise_name, remainder = _extract_exercise_name(chunk)

    # Check for "N sets x reps at weight" pattern FIRST in remainder
    sxrw = list(_SXRXW_PATTERN.finditer(remainder))
    if sxrw:
        if not exercise_name:
            exercise_name = _try_extract_trailing_exercise(remainder)
        sets_list: list[ParsedSet] = []
        for m in sxrw:
            n_sets = int(m.group(1))
            reps = int(m.group(2))
            weight = float(m.group(3))
            for _ in range(n_sets):
                sets_list.append(ParsedSet(weight=weight, reps=reps))
        if sets_list:
            return ParsedLift(
                exercise=_normalize_exercise(exercise_name) if exercise_name else "Unknown",
                sets=sets_list, raw_text=chunk,
            )

    # Then check weight x reps pattern
    wxr = list(_WXR_PATTERN.finditer(remainder))
    if wxr:
        # Check if this is actually a sets x reps at weight pattern
        if _looks_like_sets_reps(remainder, wxr):
            # Try SXRXW in the full chunk
            sxrw_full = list(_SXRXW_PATTERN.finditer(chunk))
            if sxrw_full:
                if not exercise_name:
                    exercise_name = _try_extract_trailing_exercise(chunk)
                sets_list = []
                for m in sxrw_full:
                    n_sets = int(m.group(1))
                    reps = int(m.group(2))
                    weight = float(m.group(3))
                    for _ in range(n_sets):
                        sets_list.append(ParsedSet(weight=weight, reps=reps))
                if sets_list:
                    return ParsedLift(
                        exercise=_normalize_exercise(exercise_name) if exercise_name else "Unknown",
                        sets=sets_list, raw_text=chunk,
                    )

        # Regular weight x reps
        if not exercise_name:
            exercise_name = _try_extract_trailing_exercise(remainder)
        sets_list = []
        for m in wxr:
            weight = float(m.group(1))
            reps = int(m.group(2))
            sets_list.append(ParsedSet(weight=weight, reps=reps))
        if sets_list:
            return ParsedLift(
                exercise=_normalize_exercise(exercise_name) if exercise_name else "Unknown",
                sets=sets_list, raw_text=chunk,
            )

    # Fallback: try patterns in full chunk if exercise was found
    if exercise_name:
        sxrw_full = list(_SXRXW_PATTERN.finditer(chunk))
        if sxrw_full:
            sets_list = []
            for m in sxrw_full:
                n_sets = int(m.group(1))
                reps = int(m.group(2))
                weight = float(m.group(3))
                for _ in range(n_sets):
                    sets_list.append(ParsedSet(weight=weight, reps=reps))
            if sets_list:
                return ParsedLift(
                    exercise=_normalize_exercise(exercise_name),
                    sets=sets_list, raw_text=chunk,
                )
        wxr_full = list(_WXR_PATTERN.finditer(chunk))
        if wxr_full:
            sets_list = []
            for m in wxr_full:
                weight = float(m.group(1))
                reps = int(m.group(2))
                sets_list.append(ParsedSet(weight=weight, reps=reps))
            if sets_list:
                return ParsedLift(
                    exercise=_normalize_exercise(exercise_name),
                    sets=sets_list, raw_text=chunk,
                )

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class LiftParser:
    @staticmethod
    def parse(text: str) -> list[ParsedLift]:
        text = text.strip()
        if not text:
            return []
        # Try parsing the whole text first
        whole = _parse_single_chunk(text)
        if whole is not None and whole.set_count > 1:
            return [whole]
        # Split on commas/semicolons and carry exercise name forward
        chunks = re.split(r"[;,]|\band\b", text)
        results: list[ParsedLift] = []
        last_exercise = ""
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            parsed = _parse_single_chunk(chunk)
            if parsed is not None:
                if parsed.exercise == "Unknown" and last_exercise:
                    parsed = ParsedLift(
                        exercise=last_exercise,
                        sets=parsed.sets,
                        raw_text=parsed.raw_text,
                    )
                last_exercise = parsed.exercise
                results.append(parsed)
        if not results:
            parsed = _parse_single_chunk(text)
            if parsed is not None:
                results.append(parsed)
        return results


def is_lift_log(text: str) -> bool:
    text_lower = text.lower()
    if _WXR_PATTERN.search(text):
        if any(alias in text_lower for alias in _EXERCISE_KEYWORDS):
            return True
        if _SXRXW_PATTERN.search(text):
            return True
    if _SXRXW_PATTERN.search(text):
        return True
    return False
