"""PathForge service layer — centralized data access and business logic helpers."""

import json
from typing import Any


def parse_problem_pattern(problem: dict) -> list:
    """Parse the `pattern` field from a problem dict into a Python list.

    The `problems.pattern` column is TEXT storing a JSON array string like
    ``'["hash_map_lookup"]'``. This function deserializes it exactly once
    at the service boundary so that business logic never calls ``json.loads``
    directly on raw DB values.

    Accepts already-parsed lists (e.g. from JSONB columns or test fixtures)
    as a transparent pass-through.

    Returns an empty list on any parse failure (missing key, ``None``,
    malformed JSON).
    """
    raw = problem.get("pattern")
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    return []
