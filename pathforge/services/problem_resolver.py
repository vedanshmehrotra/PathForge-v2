"""Problem Resolver — single entry point for problem-aware analysis.

This is the ONLY module allowed to:
- call GraphQL (cache-fill on first encounter)
- invoke ground truth generation

Runtime analysis must never call GraphQL or the LLM directly.
Every other service reads from the DB only.
"""
import json
from dataclasses import dataclass, field
from typing import Any, Optional

from pathforge.db.profile_manager import iso_now
from pathforge.llm.graphql_client import (
    fetch_problem_by_slug,
    fetch_title_slug_by_id,
    html_to_plain_text,
)


@dataclass
class ProblemContext:
    leetcode_id: int
    title_slug: str
    title: str
    difficulty: str
    topics: list
    description: str
    accepted_solution_groups: list = field(default_factory=list)
    ground_truth_confidence: dict = field(default_factory=dict)


def resolve_problem(
    connection,
    leetcode_id: Optional[int] = None,
    title_slug: Optional[str] = None,
) -> ProblemContext:
    """Resolve a problem identifier (numeric ID or title_slug) to a ProblemContext.

    Cache-fill path (first time only):
        1. Look up in problems table
        2. If missing -> GraphQL fetch + store
        3. Check problem_ground_truth table
        4. If missing -> LLM ground truth generation + store

    Cache-hit path (every subsequent time):
        1. Load from problems table
        2. Load from problem_ground_truth table
    """
    row = _find_problem_in_db(connection, leetcode_id, title_slug)

    if row is None:
        row = _fetch_and_store_problem(connection, leetcode_id, title_slug)

    pid = row["id"]
    slug = row.get("title_slug") or ""

    _ensure_ground_truth(connection, row)

    groups, confidence = _load_ground_truth(connection, pid)

    topics = _parse_topics(row.get("topics") or "")
    description = row.get("description") or ""

    return ProblemContext(
        leetcode_id=pid,
        title_slug=slug,
        title=row["title"],
        difficulty=row["difficulty"],
        topics=topics,
        description=description,
        accepted_solution_groups=groups,
        ground_truth_confidence=confidence,
    )


def _find_problem_in_db(connection, leetcode_id, title_slug):
    if leetcode_id is not None:
        row = connection.execute(
            "SELECT * FROM problems WHERE id = %s", (leetcode_id,)
        ).fetchone()
        if row:
            return dict(row)
    if title_slug:
        row = connection.execute(
            "SELECT * FROM problems WHERE title_slug = %s", (title_slug,)
        ).fetchone()
        if row:
            return dict(row)
    if leetcode_id is not None and title_slug:
        row = connection.execute(
            "SELECT * FROM problems WHERE id = %s OR title_slug = %s",
            (leetcode_id, title_slug),
        ).fetchone()
        if row:
            return dict(row)
    return None


def _fetch_and_store_problem(connection, leetcode_id, title_slug):
    if title_slug is None:
        if leetcode_id is not None:
            slug = fetch_title_slug_by_id(leetcode_id)
            if not slug:
                raise ValueError(
                    f"Cannot resolve LeetCode ID {leetcode_id} to a title slug"
                )
            title_slug = slug
        else:
            raise ValueError("Either leetcode_id or title_slug is required")

    existing = connection.execute(
        "SELECT * FROM problems WHERE title_slug = %s", (title_slug,)
    ).fetchone()
    if existing is not None:
        return dict(existing)

    data = fetch_problem_by_slug(title_slug)
    if data is None:
        raise ValueError(
            f"Cannot fetch problem data for '{title_slug}' from LeetCode"
        )

    qid = int(data["questionId"])
    description = html_to_plain_text(data.get("content") or "")
    now = iso_now()
    topics = ", ".join(
        t["name"] for t in (data.get("topicTags") or [])
    )
    link = f"https://leetcode.com/problems/{title_slug}/"

    connection.execute(
        """
        INSERT INTO problems
            (id, title, difficulty, topics, title_slug, description,
             pattern, test_cases, link, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT(id) DO UPDATE SET
            title = EXCLUDED.title,
            difficulty = EXCLUDED.difficulty,
            topics = EXCLUDED.topics,
            title_slug = EXCLUDED.title_slug,
            description = EXCLUDED.description,
            link = EXCLUDED.link,
            updated_at = EXCLUDED.updated_at
        """,
        (
            qid,
            data["title"],
            data["difficulty"],
            topics,
            title_slug,
            description,
            json.dumps([]),
            json.dumps(
                [
                    line.strip()
                    for line in (data.get("exampleTestcases") or "").split("\n")
                    if line.strip()
                ]
            ),
            link,
            now,
            now,
        ),
    )
    connection.commit()

    row = connection.execute(
        "SELECT * FROM problems WHERE id = %s", (qid,)
    ).fetchone()
    return dict(row)


def _ensure_ground_truth(connection, row):
    pid = row["id"]
    existing = connection.execute(
        "SELECT 1 FROM problem_ground_truth WHERE problem_id = %s", (pid,)
    ).fetchone()
    if existing:
        return

    description = row.get("description") or ""
    build_source = description or row.get("title", "")

    from pathforge.services.ground_truth_builder import build_ground_truth

    build_ground_truth(pid, build_source, connection)
    connection.commit()


def _load_ground_truth(connection, problem_id):
    row = connection.execute(
        "SELECT patterns, confidence, solution_groups, validation_status FROM problem_ground_truth WHERE problem_id = %s",
        (problem_id,),
    ).fetchone()
    if row is None:
        return [], {}

    patterns_raw = row["patterns"]
    confidence_raw = row["confidence"]
    solution_groups_raw = row["solution_groups"] if "solution_groups" in row.keys() else None
    validation_status = row["validation_status"] if "validation_status" in row.keys() else None

    # Phase 3B: if solution_groups column exists and has data, use it directly
    if solution_groups_raw is not None:
        sg = _parse_json_field(solution_groups_raw)
        if isinstance(sg, list) and sg:
            groups = []
            all_confidence = {}
            for g in sg:
                if not isinstance(g, dict):
                    continue
                # Preserve original legacy patterns for the production matcher.
                legacy_patterns = g.get("patterns", [])
                if not legacy_patterns:
                    legacy_patterns = g.get("required", [])

                # Determine required concepts for the shadow matcher.
                # If the group has a "required" field with V1 concepts, use it.
                # If it only has legacy "patterns", apply V1 vocabulary mapping.
                has_v1_required = "required" in g and g["required"]
                if has_v1_required:
                    required = g["required"]
                else:
                    required = _map_legacy_patterns_to_v1(legacy_patterns)

                groups.append({
                    "id": g.get("id", f"group_{len(groups)}"),
                    "version": g.get("version", 1),
                    "required": required,
                    "optional": g.get("optional", []),
                    "excluded": g.get("excluded", []),
                    "threshold": g.get("threshold", 0.5),
                    "authority_tier": g.get("authority_tier", g.get("evidence", validation_status or "unobserved")),
                    "provenance": g.get("provenance", []),
                    # Legacy fields for backward compatibility
                    "patterns": legacy_patterns,
                    "evidence": g.get("evidence", g.get("authority_tier", "unobserved")),
                    "confidence": g.get("confidence", {}),
                })
                all_confidence.update(g.get("confidence", {}))
            if groups:
                return groups, all_confidence

    # Fallback: legacy flat patterns column
    patterns: list = []
    confidence: dict = {}

    patterns = _parse_json_list(patterns_raw)
    confidence = _parse_json_dict(confidence_raw)

    if patterns:
        # Map legacy patterns to V1 concepts for shadow matcher
        required = _map_legacy_patterns_to_v1(patterns)
        best_conf = max(confidence.values()) if confidence else 1.0
        groups = [
            {
                "id": "group_0",
                "required": required,
                "optional": [],
                "excluded": [],
                "patterns": patterns,
                "evidence": validation_status or "unobserved",
                "confidence": {p: confidence.get(p, best_conf) for p in patterns},
            }
        ]
        return groups, confidence

    return [], {}


def _map_legacy_patterns_to_v1(patterns: list) -> list:
    """Map legacy pattern IDs to V1 technique/strategy concepts.

    Uses the same PATTERN_TO_V1_MAPPING from the ground truth builder.
    This ensures that even legacy groups stored before Phase 4A can produce
    V1 concept IDs for the shadow matcher.
    """
    from pathforge.services.ground_truth_builder import PATTERN_TO_V1_MAPPING

    required = set()
    for pattern in patterns:
        mapping = PATTERN_TO_V1_MAPPING.get(pattern)
        if mapping and mapping.get("required"):
            required.update(mapping["required"])
    return sorted(required) if required else []


def _parse_json_field(raw):
    """Parse a value that may be str (TEXT) or already-parsed (JSONB)."""
    if isinstance(raw, str) and raw:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
    return raw


def _parse_json_list(raw):
    """Parse a JSON list from TEXT or JSONB."""
    val = _parse_json_field(raw)
    return val if isinstance(val, list) else []


def _parse_json_dict(raw):
    """Parse a JSON dict from TEXT or JSONB."""
    val = _parse_json_field(raw)
    return val if isinstance(val, dict) else {}


def _parse_topics(raw: str) -> list:
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return [t.strip() for t in raw.split(",") if t.strip()]
