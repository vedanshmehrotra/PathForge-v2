"""Ground truth builder — generates structured solution groups from LLM output.

Phase 4A: Multi-group generation with V1 vocabulary mapping and validation.
"""
import json

from pathforge.ast_engine.patterns import ALL_PATTERNS
from pathforge.db.profile_manager import iso_now
from pathforge.llm.openrouter_client import call_llm


class GroundTruthError(Exception):
    """Raised when ground truth generation fails (LLM unavailable, bad response, etc.)."""


# ============================================================
# V1 Vocabulary Registry
# ============================================================

# Valid technique IDs from PATHFORGE_TECHNIQUE_STRATEGY_VOCABULARY_V1.md
VALID_TECHNIQUES = {
    "sequential_accumulation",
    "bidirectional_index_scan",
    "recursive_branching",
    "carry_propagation",
    "loop_state_tracking",
    "iterative_table_filling",
    "linked_list_traversal",       # Phase 5A
    "fixed_window_maintenance",    # Phase 5A
    "monotonic_stack_maintenance", # Phase 5A
}

# Valid strategy IDs from PATHFORGE_TECHNIQUE_STRATEGY_VOCABULARY_V1.md
VALID_STRATEGIES = {
    "binary_search",
    "sliding_window",
    "two_pointers_opposite",
    "dfs_backtracking",
    "dp_top_down",
    "dp_bottom_up",
    "bfs_shortest_path",
    "union_find",
    "monotonic_stack_strategy",    # Phase 5A
}

# All valid V1 concept IDs (techniques + strategies)
VALID_V1_CONCEPTS = VALID_TECHNIQUES | VALID_STRATEGIES

# Valid authority tiers
VALID_AUTHORITY_TIERS = {
    "bootstrap",
    "llm_proposed",
    "structurally_observed",
    "externally_listed",
    "editorial",
}

# ============================================================
# Old pattern → V1 vocabulary mapping
# ============================================================

# Maps legacy flat pattern IDs to V1 technique/strategy concepts.
# Each mapping produces required/optional/excluded lists.
# If a pattern cannot be mapped, it is preserved in diagnostic metadata.
PATTERN_TO_V1_MAPPING = {
    # Arrays & Hashing
    "hash_map_lookup": {
        "required": [],
        "optional": [],
        "excluded": [],
        "note": "Generic data-structure behavior, not a V1 technique",
    },
    "hash_map_frequency": {
        "required": [],
        "optional": [],
        "excluded": [],
        "note": "Generic data-structure behavior, not a V1 technique",
    },
    "prefix_sum": {
        "required": ["sequential_accumulation"],
        "optional": ["iterative_table_filling"],
        "excluded": [],
        "note": "Prefix sum maps to sequential accumulation + optional table filling",
    },
    "sliding_window_fixed": {
        "required": ["sliding_window"],
        "optional": ["loop_state_tracking"],
        "excluded": ["two_pointers_opposite"],
        "note": "Fixed sliding window maps to sliding_window strategy",
    },
    "sliding_window_variable": {
        "required": ["sliding_window"],
        "optional": ["loop_state_tracking"],
        "excluded": ["two_pointers_opposite"],
        "note": "Variable sliding window maps to sliding_window strategy",
    },
    "two_pointers_opposite": {
        "required": ["two_pointers_opposite"],
        "optional": ["bidirectional_index_scan"],
        "excluded": ["binary_search"],
        "note": "Maps directly to two_pointers_opposite strategy",
    },
    "two_pointers_same": {
        "required": ["bidirectional_index_scan"],
        "optional": [],
        "excluded": ["two_pointers_opposite"],
        "note": "Same-direction two pointers maps to bidirectional_index_scan technique",
    },
    # Graphs & Trees
    "dfs_recursive": {
        "required": ["recursive_branching"],
        "optional": ["dfs_backtracking"],
        "excluded": ["bfs_shortest_path"],
        "note": "Recursive DFS maps to recursive_branching technique",
    },
    "dfs_iterative": {
        "required": [],
        "optional": [],
        "excluded": ["recursive_branching"],
        "note": "Iterative DFS has no direct V1 technique equivalent",
    },
    "bfs_level_order": {
        "required": ["bfs_shortest_path"],
        "optional": ["loop_state_tracking"],
        "excluded": ["recursive_branching"],
        "note": "Level-order BFS maps to bfs_shortest_path strategy",
    },
    "bfs_shortest_path": {
        "required": ["bfs_shortest_path"],
        "optional": [],
        "excluded": ["recursive_branching"],
        "note": "Maps directly to bfs_shortest_path strategy",
    },
    "topological_sort": {
        "required": [],
        "optional": ["bfs_shortest_path"],
        "excluded": [],
        "note": "No direct V1 technique; uses BFS-like traversal",
    },
    "union_find": {
        "required": ["union_find"],
        "optional": [],
        "excluded": [],
        "note": "Maps directly to union_find strategy",
    },
    "binary_search_tree": {
        "required": ["binary_search"],
        "optional": [],
        "excluded": ["two_pointers_opposite"],
        "note": "BST operations map to binary_search strategy",
    },
    # Dynamic Programming
    "dp_1d_forward": {
        "required": ["dp_bottom_up"],
        "optional": ["iterative_table_filling"],
        "excluded": ["recursive_branching"],
        "note": "1D forward DP maps to dp_bottom_up strategy",
    },
    "dp_1d_sequence": {
        "required": ["dp_bottom_up"],
        "optional": ["iterative_table_filling"],
        "excluded": ["recursive_branching"],
        "note": "1D sequence DP maps to dp_bottom_up strategy",
    },
    "dp_2d_grid": {
        "required": ["dp_bottom_up"],
        "optional": ["iterative_table_filling"],
        "excluded": ["recursive_branching"],
        "note": "2D grid DP maps to dp_bottom_up strategy",
    },
    "dp_2d_string": {
        "required": ["dp_bottom_up"],
        "optional": ["iterative_table_filling"],
        "excluded": ["recursive_branching"],
        "note": "2D string DP maps to dp_bottom_up strategy",
    },
    "dp_knapsack": {
        "required": ["dp_bottom_up"],
        "optional": ["iterative_table_filling"],
        "excluded": ["recursive_branching"],
        "note": "Knapsack DP maps to dp_bottom_up strategy",
    },
    "dp_interval": {
        "required": ["dp_bottom_up"],
        "optional": ["iterative_table_filling"],
        "excluded": ["recursive_branching"],
        "note": "Interval DP maps to dp_bottom_up strategy",
    },
    "dp_state_machine": {
        "required": ["dp_bottom_up"],
        "optional": ["iterative_table_filling"],
        "excluded": ["recursive_branching"],
        "note": "State machine DP maps to dp_bottom_up strategy",
    },
    # Linked Lists & Stack
    "fast_slow_pointers": {
        "required": ["bidirectional_index_scan"],
        "optional": [],
        "excluded": [],
        "note": "Fast/slow pointers map to bidirectional_index_scan technique",
    },
    "linked_list_reversal": {
        "required": [],
        "optional": ["carry_propagation"],
        "excluded": ["two_pointers_opposite"],
        "note": "No direct V1 technique for reversal; preserve as unresolved",
    },
    "monotonic_stack": {
        "required": [],
        "optional": [],
        "excluded": [],
        "note": "No direct V1 technique for monotonic stack",
    },
    "monotonic_deque": {
        "required": [],
        "optional": [],
        "excluded": [],
        "note": "No direct V1 technique for monotonic deque",
    },
    # Binary Search
    "binary_search_standard": {
        "required": ["binary_search"],
        "optional": ["bidirectional_index_scan"],
        "excluded": ["two_pointers_opposite"],
        "note": "Maps directly to binary_search strategy",
    },
    "binary_search_rotated": {
        "required": ["binary_search"],
        "optional": ["bidirectional_index_scan"],
        "excluded": ["two_pointers_opposite"],
        "note": "Maps to binary_search strategy (rotated variant)",
    },
    "binary_search_answer": {
        "required": ["binary_search"],
        "optional": ["bidirectional_index_scan"],
        "excluded": ["two_pointers_opposite"],
        "note": "Maps to binary_search strategy (answer-space variant)",
    },
    # Heap / Greedy / Backtracking
    "heap_top_k": {
        "required": [],
        "optional": [],
        "excluded": [],
        "note": "No direct V1 technique for heap operations",
    },
    "greedy_local": {
        "required": [],
        "optional": ["sequential_accumulation"],
        "excluded": [],
        "note": "No direct V1 technique for greedy; may use accumulation",
    },
    "greedy_interval": {
        "required": [],
        "optional": [],
        "excluded": [],
        "note": "No direct V1 technique for interval greedy",
    },
    "backtracking_permutation": {
        "required": ["dfs_backtracking"],
        "optional": ["recursive_branching"],
        "excluded": ["dp_top_down"],
        "note": "Maps to dfs_backtracking strategy",
    },
    "backtracking_subset": {
        "required": ["dfs_backtracking"],
        "optional": ["recursive_branching"],
        "excluded": ["dp_top_down"],
        "note": "Maps to dfs_backtracking strategy",
    },
}


def build_ground_truth(problem_id: int, problem_description: str, connection) -> list[str]:
    """Generate ground truth for a problem.

    Returns the canonical pattern list (legacy format) for backward compatibility.
    Also stores structured solution groups in the database.
    """
    raw = call_llm(problem_description)

    if raw is None:
        raise GroundTruthError(
            "Ground truth generation failed: OpenRouter/LLM unavailable or returned no valid output"
        )

    patterns = raw.get("patterns", [])
    confidence = raw.get("confidence", {})
    approaches = raw.get("approaches", [])  # Optional: LLM may propose multiple approaches

    canonical, filtered_confidence = _normalize_patterns(patterns, confidence)

    _store_ground_truth(connection, problem_id, canonical, filtered_confidence, approaches)

    return canonical


def _normalize_patterns(
    patterns: list,
    confidence: dict,
) -> tuple[list[str], dict]:
    canonical_set = {p.lower().replace("-", "_").replace(" ", "_") for p in patterns}

    canonical = []
    filtered_confidence = {}
    for p in canonical_set:
        if p in ALL_PATTERNS:
            canonical.append(p)
            if p in confidence:
                filtered_confidence[p] = _clamp_confidence(confidence[p])
            elif any(k.replace("-", "_").replace(" ", "_") == p for k in confidence):
                key = next(k for k in confidence if k.replace("-", "_").replace(" ", "_") == p)
                filtered_confidence[p] = _clamp_confidence(confidence[key])

    return canonical, filtered_confidence


def _clamp_confidence(value) -> float:
    try:
        v = float(value)
        return max(0.0, min(1.0, v))
    except (TypeError, ValueError):
        return 0.5


# ============================================================
# Multi-group generation
# ============================================================

def _build_solution_groups(
    patterns: list[str],
    confidence: dict,
    approaches: list = None,
) -> list[dict]:
    """Build structured solution groups from LLM-proposed patterns.

    Phase 4A: Multi-group generation with V1 vocabulary mapping.

    Each group represents a distinct valid solution approach.
    Groups are validated against the V1 vocabulary before storage.

    Args:
        patterns: Legacy flat pattern list from LLM
        confidence: Confidence scores per pattern
        approaches: Optional list of distinct approaches from LLM
    """
    if not patterns and not approaches:
        return []

    groups = []

    # If LLM provided distinct approaches, use them for multi-group generation
    if approaches and len(approaches) > 1:
        for i, approach in enumerate(approaches):
            approach_patterns = approach.get("patterns", [])
            approach_name = approach.get("name", f"approach_{i}")
            approach_confidence = approach.get("confidence", confidence)

            group = _build_single_group(
                group_id=f"group_{i}",
                patterns=approach_patterns,
                confidence=approach_confidence,
                approach_name=approach_name,
            )
            if group is not None:
                groups.append(group)
    else:
        # Single approach: group all patterns together
        # But also check if patterns can be split into distinct strategy groups
        groups = _split_patterns_into_groups(patterns, confidence)

    # Validate all groups
    validated_groups = []
    for group in groups:
        validation = _validate_group(group)
        if validation["valid"]:
            group["validation"] = "accepted"
            validated_groups.append(group)
        else:
            group["validation"] = "rejected"
            group["validation_reason"] = validation["reason"]
            # Still include rejected groups for diagnostic purposes
            # but mark them clearly
            validated_groups.append(group)

    return validated_groups


def _build_single_group(
    group_id: str,
    patterns: list[str],
    confidence: dict,
    approach_name: str = "",
) -> dict:
    """Build a single solution group from patterns.

    Maps legacy patterns to V1 vocabulary concepts.
    """
    if not patterns:
        return None

    # Map patterns to V1 concepts
    required = set()
    optional = set()
    excluded = set()
    unmapped_patterns = []

    for pattern in patterns:
        mapping = PATTERN_TO_V1_MAPPING.get(pattern)
        if mapping:
            required.update(mapping["required"])
            optional.update(mapping["optional"])
            excluded.update(mapping["excluded"])
        else:
            unmapped_patterns.append(pattern)

    # Remove excluded from required/optional
    required -= excluded
    optional -= excluded
    # Remove required from optional (required takes priority)
    optional -= required

    return {
        "id": group_id,
        "version": 1,
        "required": sorted(required),
        "optional": sorted(optional),
        "excluded": sorted(excluded),
        "threshold": 0.5,
        "authority_tier": "llm_proposed",
        "provenance": [
            "llm_ground_truth",
            f"vocabulary_v1",
        ],
        "approach_name": approach_name,
        "unmapped_patterns": unmapped_patterns,
        # Legacy fields for backward compatibility
        "patterns": patterns,
        "evidence": "llm_proposed",
        "confidence": {p: confidence.get(p, 0.5) for p in patterns},
    }


def _split_patterns_into_groups(
    patterns: list[str],
    confidence: dict,
) -> list[dict]:
    """Split patterns into distinct strategy groups where possible.

    Patterns that map to the same V1 strategy are grouped together.
    Patterns that map to different strategies form separate groups.
    """
    if not patterns:
        return []

    # Group patterns by their primary strategy
    strategy_groups = {}
    unmapped = []

    for pattern in patterns:
        mapping = PATTERN_TO_V1_MAPPING.get(pattern)
        if mapping and mapping["required"]:
            # Find the primary strategy (first strategy in required list)
            primary = None
            for concept in mapping["required"]:
                if concept in VALID_STRATEGIES:
                    primary = concept
                    break
            if primary is None:
                primary = mapping["required"][0]

            if primary not in strategy_groups:
                strategy_groups[primary] = []
            strategy_groups[primary].append(pattern)
        else:
            unmapped.append(pattern)

    groups = []

    # Create a group for each strategy cluster
    for i, (strategy, group_patterns) in enumerate(sorted(strategy_groups.items())):
        group = _build_single_group(
            group_id=f"group_{i}",
            patterns=group_patterns,
            confidence=confidence,
            approach_name=strategy,
        )
        if group is not None:
            groups.append(group)

    # If there are unmapped patterns, create a fallback group
    if unmapped and not groups:
        group = _build_single_group(
            group_id="group_0",
            patterns=unmapped,
            confidence=confidence,
            approach_name="unmapped",
        )
        if group is not None:
            groups.append(group)
    elif unmapped:
        # Add unmapped patterns to the first group as optional
        if groups:
            for pattern in unmapped:
                mapping = PATTERN_TO_V1_MAPPING.get(pattern)
                if mapping:
                    groups[0]["optional"].extend(mapping.get("optional", []))
            groups[0]["optional"] = sorted(set(groups[0]["optional"]))
            groups[0]["unmapped_patterns"] = unmapped

    return groups if groups else [_build_single_group(
        group_id="group_0",
        patterns=patterns,
        confidence=confidence,
        approach_name="fallback",
    )]


# ============================================================
# Structural validation
# ============================================================

def _validate_group(group: dict) -> dict:
    """Validate a solution group against the V1 vocabulary.

    Returns {"valid": True/False, "reason": "...", "warnings": [...]}.
    
    Validation outcomes:
    - valid: group passes all checks
    - rejected: group has fatal errors (invalid IDs, conflicts)
    - warning: group has non-fatal issues (unsatisfiable combinations)
    """
    required = group.get("required", [])
    optional = group.get("optional", [])
    excluded = group.get("excluded", [])
    threshold = group.get("threshold", 0.5)
    warnings = []

    # Check threshold bounds
    if not (0.0 <= threshold <= 1.0):
        return {"valid": False, "reason": f"threshold {threshold} out of bounds [0.0, 1.0]", "warnings": []}

    # Check all required IDs are valid V1 concepts
    for concept_id in required:
        if concept_id not in VALID_V1_CONCEPTS:
            return {"valid": False, "reason": f"required concept '{concept_id}' not in V1 vocabulary", "warnings": []}

    # Check all optional IDs are valid V1 concepts
    for concept_id in optional:
        if concept_id not in VALID_V1_CONCEPTS:
            return {"valid": False, "reason": f"optional concept '{concept_id}' not in V1 vocabulary", "warnings": []}

    # Check all excluded IDs are valid V1 concepts
    for concept_id in excluded:
        if concept_id not in VALID_V1_CONCEPTS:
            return {"valid": False, "reason": f"excluded concept '{concept_id}' not in V1 vocabulary", "warnings": []}

    # Check no concept is both required and excluded
    required_set = set(required)
    excluded_set = set(excluded)
    overlap = required_set & excluded_set
    if overlap:
        return {"valid": False, "reason": f"concepts {overlap} are both required and excluded", "warnings": []}

    # Check authority tier is valid
    authority_tier = group.get("authority_tier", "")
    if authority_tier not in VALID_AUTHORITY_TIERS:
        return {"valid": False, "reason": f"authority_tier '{authority_tier}' not valid", "warnings": []}

    # Check no concept is both optional and excluded
    optional_set = set(optional)
    overlap = optional_set & excluded_set
    if overlap:
        return {"valid": False, "reason": f"concepts {overlap} are both optional and excluded", "warnings": []}

    # Phase 5B: Semantic coherence checks
    # Check for mutually exclusive required strategies
    from pathforge.ast_analysis.shadow.coherence import (
        check_mutual_exclusion, check_unsatisfiable_combinations,
    )

    # Collect required strategies only (not techniques)
    required_strategies = [c for c in required if c in VALID_STRATEGIES]

    # Check mutual exclusion (fatal — rejected)
    exclusions = check_mutual_exclusion(required_strategies)
    if exclusions:
        reasons = [f"{a} ↔ {b}: {r}" for a, b, r in exclusions]
        return {
            "valid": False,
            "reason": f"mutually exclusive strategies: {'; '.join(reasons)}",
            "warnings": [],
        }

    # Check unsatisfiable combinations (warnings — not rejected)
    unsatisfiable = check_unsatisfiable_combinations(required_strategies)
    for strat_a, strat_b, reason in unsatisfiable:
        warnings.append(f"unsatisfiable: {strat_a} + {strat_b}: {reason}")

    return {"valid": True, "reason": "", "warnings": warnings}


def validate_solution_groups(groups: list[dict]) -> list[dict]:
    """Validate a list of solution groups.

    Returns the same list with validation_status added to each group.
    Groups may have validation_status of: accepted, rejected, or warning.
    """
    validated = []
    for group in groups:
        result = _validate_group(group)
        if result["valid"]:
            if result.get("warnings"):
                group["validation"] = "warning"
                group["validation_warnings"] = result["warnings"]
            else:
                group["validation"] = "accepted"
        else:
            group["validation"] = "rejected"
        group["validation_reason"] = result["reason"]
        validated.append(group)
    return validated


# ============================================================
# Storage
# ============================================================

def _store_ground_truth(
    connection,
    problem_id: int,
    patterns: list[str],
    confidence: dict,
    approaches: list = None,
):
    """Store ground truth with both legacy flat columns and new solution_groups."""
    now = iso_now()
    patterns_json = json.dumps(patterns)
    confidence_json = json.dumps(confidence) if confidence else "{}"

    # Phase 4A: multi-group structured solution groups with V1 vocabulary
    solution_groups = _build_solution_groups(patterns, confidence, approaches)
    solution_groups_json = json.dumps(solution_groups)

    connection.execute(
        """
        INSERT INTO problem_ground_truth (problem_id, patterns, confidence, solution_groups, validation_status, created_at, updated_at)
        VALUES (%s, %s, %s, %s, 'llm_proposed', COALESCE((SELECT created_at FROM problem_ground_truth WHERE problem_id = %s), %s), %s)
        ON CONFLICT(problem_id) DO UPDATE SET
            patterns = EXCLUDED.patterns,
            confidence = EXCLUDED.confidence,
            solution_groups = EXCLUDED.solution_groups,
            updated_at = EXCLUDED.updated_at
        """,
        (problem_id, patterns_json, confidence_json, solution_groups_json, problem_id, now, now),
    )
