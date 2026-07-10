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
            "SELECT * FROM problems WHERE id = ?", (leetcode_id,)
        ).fetchone()
        if row:
            return dict(row)
    if title_slug:
        row = connection.execute(
            "SELECT * FROM problems WHERE title_slug = ?", (title_slug,)
        ).fetchone()
        if row:
            return dict(row)
    if leetcode_id is not None and title_slug:
        row = connection.execute(
            "SELECT * FROM problems WHERE id = ? OR title_slug = ?",
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
        INSERT OR REPLACE INTO problems
            (id, title, difficulty, topics, title_slug, description,
             pattern, test_cases, link, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            qid,
            data["title"],
            data["difficulty"],
            topics,
            title_slug,
            description,
            "[]",
            data.get("exampleTestcases") or "",
            link,
            now,
            now,
        ),
    )
    connection.commit()

    row = connection.execute(
        "SELECT * FROM problems WHERE id = ?", (qid,)
    ).fetchone()
    return dict(row)


def _ensure_ground_truth(connection, row):
    pid = row["id"]
    existing = connection.execute(
        "SELECT 1 FROM problem_ground_truth WHERE problem_id = ?", (pid,)
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
        "SELECT patterns, confidence FROM problem_ground_truth WHERE problem_id = ?",
        (problem_id,),
    ).fetchone()
    if row is None:
        return [], {}

    patterns_raw = row["patterns"]
    confidence_raw = row["confidence"]

    patterns: list = []
    confidence: dict = {}

    if isinstance(patterns_raw, str) and patterns_raw:
        try:
            parsed = json.loads(patterns_raw)
            if isinstance(parsed, list):
                patterns = parsed
        except (json.JSONDecodeError, TypeError):
            patterns = []

    if isinstance(confidence_raw, str) and confidence_raw:
        try:
            confidence = json.loads(confidence_raw)
        except (json.JSONDecodeError, TypeError):
            confidence = {}

    if patterns:
        best_conf = max(confidence.values()) if confidence else 1.0
        groups = [
            {
                "id": "group_0",
                "display_name": "Primary Solution",
                "confidence": best_conf,
                "patterns": patterns,
            }
        ]
        return groups, confidence

    return [], {}


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
