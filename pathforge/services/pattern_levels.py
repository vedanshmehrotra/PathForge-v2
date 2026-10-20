"""A presentation of existing pattern Elo; no separate XP or scoring engine."""
import math

from pathforge.elo_engine import MIN_ELO

POINTS_PER_LEVEL = 200


def pattern_level(rating: float) -> dict:
    value = float(rating)
    if not math.isfinite(value):
        raise ValueError("Pattern rating must be finite")
    experience = round(max(0.0, value - MIN_ELO), 2)
    level_index = math.floor(experience / POINTS_PER_LEVEL)
    into_level = round(experience - level_index * POINTS_PER_LEVEL, 2)
    return {
        "level": level_index + 1,
        "experience": experience,
        "into_level": into_level,
        "points_per_level": POINTS_PER_LEVEL,
        "progress_percent": math.floor(into_level / POINTS_PER_LEVEL * 10000) / 100,
    }
