"""Seed authoritative ground truth for 18 commonly used problems.

Uses existing CSV patterns + V1 mapping. Does NOT call the LLM.
Authority tier: structurally_observed (manually verified).
"""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pathforge.services.ground_truth_builder import (
    _validate_group,
    VALID_STRATEGIES,
    VALID_TECHNIQUES,
)
from pathforge.db.db import get_connection
from pathforge.db.profile_manager import iso_now


# ============================================================
# Seeded solution groups — manually verified, no LLM involved
# ============================================================

# Each entry: (problem_id, title_slug, csv_pattern, groups)
# groups is a list of solution group dicts

SEEDED_PROBLEMS = [
    # --- SLIDING WINDOW ---
    (3, "longest-substring-without-repeating-characters", "sliding_window_variable", [
        {
            "id": "group_0",
            "version": 1,
            "required": ["sliding_window"],
            "optional": ["loop_state_tracking"],
            "excluded": ["two_pointers_opposite"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["manual_verification", "vocabulary_v1"],
            "approach_name": "sliding_window",
            "patterns": ["sliding_window_variable"],
            "evidence": "structurally_observed",
            "confidence": {"sliding_window_variable": 0.95},
        },
    ]),
    (209, "minimum-size-subarray-sum", "sliding_window_variable", [
        {
            "id": "group_0",
            "version": 1,
            "required": ["sliding_window"],
            "optional": ["loop_state_tracking"],
            "excluded": ["two_pointers_opposite"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["manual_verification", "vocabulary_v1"],
            "approach_name": "sliding_window",
            "patterns": ["sliding_window_variable"],
            "evidence": "structurally_observed",
            "confidence": {"sliding_window_variable": 0.95},
        },
    ]),
    (2958, "max-subarray-length-of-length-k", "sliding_window_variable", [
        {
            "id": "group_0",
            "version": 1,
            "required": ["sliding_window"],
            "optional": ["loop_state_tracking"],
            "excluded": ["two_pointers_opposite"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["manual_verification", "vocabulary_v1"],
            "approach_name": "sliding_window",
            "patterns": ["sliding_window_variable"],
            "evidence": "structurally_observed",
            "confidence": {"sliding_window_variable": 0.95},
        },
    ]),

    # --- TWO POINTERS ---
    (11, "container-with-most-water", "two_pointers_opposite", [
        {
            "id": "group_0",
            "version": 1,
            "required": ["two_pointers_opposite"],
            "optional": ["bidirectional_index_scan"],
            "excluded": ["binary_search"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["manual_verification", "vocabulary_v1"],
            "approach_name": "two_pointers_opposite",
            "patterns": ["two_pointers_opposite"],
            "evidence": "structurally_observed",
            "confidence": {"two_pointers_opposite": 0.95},
        },
    ]),
    (125, "valid-palindrome", "two_pointers_opposite", [
        {
            "id": "group_0",
            "version": 1,
            "required": ["two_pointers_opposite"],
            "optional": ["bidirectional_index_scan"],
            "excluded": ["binary_search"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["manual_verification", "vocabulary_v1"],
            "approach_name": "two_pointers_opposite",
            "patterns": ["two_pointers_opposite"],
            "evidence": "structurally_observed",
            "confidence": {"two_pointers_opposite": 0.95},
        },
    ]),
    (15, "3sum", "two_pointers_opposite", [
        {
            "id": "group_0",
            "version": 1,
            "required": ["two_pointers_opposite"],
            "optional": ["bidirectional_index_scan"],
            "excluded": ["binary_search"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["manual_verification", "vocabulary_v1"],
            "approach_name": "two_pointers_opposite",
            "patterns": ["two_pointers_opposite"],
            "evidence": "structurally_observed",
            "confidence": {"two_pointers_opposite": 0.95},
        },
    ]),

    # --- BINARY SEARCH ---
    (704, "binary-search", "binary_search_standard", [
        {
            "id": "group_0",
            "version": 1,
            "required": ["binary_search"],
            "optional": ["bidirectional_index_scan"],
            "excluded": ["two_pointers_opposite"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["manual_verification", "vocabulary_v1"],
            "approach_name": "binary_search",
            "patterns": ["binary_search_standard"],
            "evidence": "structurally_observed",
            "confidence": {"binary_search_standard": 0.95},
        },
    ]),
    (35, "search-insert-position", "binary_search_standard", [
        {
            "id": "group_0",
            "version": 1,
            "required": ["binary_search"],
            "optional": ["bidirectional_index_scan"],
            "excluded": ["two_pointers_opposite"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["manual_verification", "vocabulary_v1"],
            "approach_name": "binary_search",
            "patterns": ["binary_search_standard"],
            "evidence": "structurally_observed",
            "confidence": {"binary_search_standard": 0.95},
        },
    ]),

    # --- DP BOTTOM-UP ---
    (70, "climbing-stairs", "dp_1d_forward", [
        {
            "id": "group_0",
            "version": 1,
            "required": ["dp_bottom_up"],
            "optional": ["iterative_table_filling"],
            "excluded": ["recursive_branching"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["manual_verification", "vocabulary_v1"],
            "approach_name": "dp_bottom_up",
            "patterns": ["dp_1d_forward"],
            "evidence": "structurally_observed",
            "confidence": {"dp_1d_forward": 0.95},
        },
    ]),
    (322, "coin-change", "dp_1d_forward", [
        {
            "id": "group_0",
            "version": 1,
            "required": ["dp_bottom_up"],
            "optional": ["iterative_table_filling"],
            "excluded": ["recursive_branching"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["manual_verification", "vocabulary_v1"],
            "approach_name": "dp_bottom_up",
            "patterns": ["dp_1d_forward"],
            "evidence": "structurally_observed",
            "confidence": {"dp_1d_forward": 0.95},
        },
    ]),
    (62, "unique-paths", "dp_2d_grid", [
        {
            "id": "group_0",
            "version": 1,
            "required": ["dp_bottom_up"],
            "optional": ["iterative_table_filling"],
            "excluded": ["recursive_branching"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["manual_verification", "vocabulary_v1"],
            "approach_name": "dp_bottom_up",
            "patterns": ["dp_2d_grid"],
            "evidence": "structurally_observed",
            "confidence": {"dp_2d_grid": 0.95},
        },
    ]),

    # --- DP TOP-DOWN (separate groups for memoized variants) ---
    (70, "climbing-stairs", "dp_1d_forward", [
        {
            "id": "group_1",
            "version": 1,
            "required": ["dp_top_down"],
            "optional": ["recursive_branching"],
            "excluded": ["dfs_backtracking"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["manual_verification", "vocabulary_v1"],
            "approach_name": "dp_top_down",
            "patterns": ["dp_1d_forward"],
            "evidence": "structurally_observed",
            "confidence": {"dp_1d_forward": 0.90},
        },
    ]),
    (322, "coin-change", "dp_1d_forward", [
        {
            "id": "group_1",
            "version": 1,
            "required": ["dp_top_down"],
            "optional": ["recursive_branching"],
            "excluded": ["dfs_backtracking"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["manual_verification", "vocabulary_v1"],
            "approach_name": "dp_top_down",
            "patterns": ["dp_1d_forward"],
            "evidence": "structurally_observed",
            "confidence": {"dp_1d_forward": 0.90},
        },
    ]),

    # --- DFS/BACKTRACKING ---
    (46, "permutations", "backtracking_permutation", [
        {
            "id": "group_0",
            "version": 1,
            "required": ["dfs_backtracking"],
            "optional": ["recursive_branching"],
            "excluded": ["dp_top_down"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["manual_verification", "vocabulary_v1"],
            "approach_name": "dfs_backtracking",
            "patterns": ["backtracking_permutation"],
            "evidence": "structurally_observed",
            "confidence": {"backtracking_permutation": 0.95},
        },
    ]),
    (78, "subsets", "backtracking_subset", [
        {
            "id": "group_0",
            "version": 1,
            "required": ["dfs_backtracking"],
            "optional": ["recursive_branching"],
            "excluded": ["dp_top_down"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["manual_verification", "vocabulary_v1"],
            "approach_name": "dfs_backtracking",
            "patterns": ["backtracking_subset"],
            "evidence": "structurally_observed",
            "confidence": {"backtracking_subset": 0.95},
        },
    ]),

    # --- BFS ---
    (102, "binary-tree-level-order-traversal", "bfs_level_order", [
        {
            "id": "group_0",
            "version": 1,
            "required": ["bfs_shortest_path"],
            "optional": ["loop_state_tracking"],
            "excluded": ["recursive_branching"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["manual_verification", "vocabulary_v1"],
            "approach_name": "bfs_shortest_path",
            "patterns": ["bfs_level_order"],
            "evidence": "structurally_observed",
            "confidence": {"bfs_level_order": 0.95},
        },
    ]),

    # --- MONOTONIC STACK ---
    (496, "next-greater-element-i", "monotonic_stack", [
        {
            "id": "group_0",
            "version": 1,
            "required": ["monotonic_stack_maintenance"],
            "optional": [],
            "excluded": ["sliding_window"],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["manual_verification", "vocabulary_v1"],
            "approach_name": "monotonic_stack",
            "patterns": ["monotonic_stack"],
            "evidence": "structurally_observed",
            "confidence": {"monotonic_stack": 0.95},
        },
    ]),

    # --- UNION-FIND ---
    (200, "number-of-islands", "union_find", [
        {
            "id": "group_0",
            "version": 1,
            "required": ["union_find"],
            "optional": [],
            "excluded": [],
            "threshold": 0.5,
            "authority_tier": "structurally_observed",
            "provenance": ["manual_verification", "vocabulary_v1"],
            "approach_name": "union_find",
            "patterns": ["union_find"],
            "evidence": "structurally_observed",
            "confidence": {"union_find": 0.95},
        },
    ]),
]


def validate_all_groups():
    """Validate all groups before inserting. Returns list of errors."""
    errors = []
    for pid, slug, csv_pat, groups in SEEDED_PROBLEMS:
        for g in groups:
            result = _validate_group(g)
            if not result["valid"]:
                errors.append(f"Problem {pid} ({slug}) group {g['id']}: {result['reason']}")
    return errors


def get_solution_groups_for_problem(pid):
    """Get all solution groups for a problem (may have multiple for multi-approach)."""
    groups = []
    for p_id, slug, csv_pat, p_groups in SEEDED_PROBLEMS:
        if p_id == pid:
            groups.extend(p_groups)
    return groups


def seed_all(dry_run=False):
    """Seed all problems into problem_ground_truth."""
    errors = validate_all_groups()
    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print(f"  FAIL: {e}")
        return False

    print(f"OK: All {len(SEEDED_PROBLEMS)} solution groups validated successfully")
    print()

    conn = get_connection()
    try:
        now = iso_now()
        inserted = 0
        skipped = 0

        # Group by problem_id
        problem_groups = {}
        for pid, slug, csv_pat, groups in SEEDED_PROBLEMS:
            if pid not in problem_groups:
                problem_groups[pid] = []
            problem_groups[pid].extend(groups)

        for pid, groups in sorted(problem_groups.items()):
            # Check if problem exists
            row = conn.execute("SELECT id FROM problems WHERE id = %s", (pid,)).fetchone()
            if not row:
                print(f"  WARN: Problem {pid} not in problems table - skipping")
                skipped += 1
                continue

            # Check existing ground truth
            existing = conn.execute(
                "SELECT solution_groups FROM problem_ground_truth WHERE problem_id = %s",
                (pid,),
            ).fetchone()

            groups_json = json.dumps(groups)

            if existing:
                # Merge: keep existing groups that aren't overwritten
                old_sg = existing["solution_groups"]
                if isinstance(old_sg, str):
                    old_sg = json.loads(old_sg)
                if isinstance(old_sg, list):
                    # Keep groups with IDs not in the new set
                    new_ids = {g["id"] for g in groups}
                    merged = [g for g in old_sg if g.get("id") not in new_ids]
                    merged.extend(groups)
                    groups_json = json.dumps(merged)
                    print(f"  MERGE: Problem {pid}: merged with {len(old_sg)} existing groups -> {len(merged)} total")
                else:
                    print(f"  REPLACE: Problem {pid}: replacing {type(old_sg)} with {len(groups)} groups")
            else:
                print(f"  NEW: Problem {pid}: ({len(groups)} groups)")

            if not dry_run:
                conn.execute(
                    """
                    INSERT INTO problem_ground_truth
                        (problem_id, patterns, confidence, solution_groups,
                         validation_status, created_at, updated_at)
                    VALUES (%s, '[]', '{}', %s, 'structurally_observed', %s, %s)
                    ON CONFLICT(problem_id) DO UPDATE SET
                        solution_groups = EXCLUDED.solution_groups,
                        validation_status = EXCLUDED.validation_status,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (pid, groups_json, now, now),
                )
            inserted += 1

        if not dry_run:
            conn.commit()
            print(f"\nDONE: Inserted {inserted} problems into problem_ground_truth")
        else:
            print(f"\nDRY RUN: would insert {inserted} problems")

        if skipped:
            print(f"WARN: Skipped {skipped} problems (not in problems table)")

        return True

    finally:
        conn.close()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("=== DRY RUN — no changes will be made ===\n")
    success = seed_all(dry_run=dry_run)
    sys.exit(0 if success else 1)
