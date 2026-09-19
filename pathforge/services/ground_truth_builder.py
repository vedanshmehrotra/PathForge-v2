"""Ground truth builder — generates structured solution groups from LLM output.

Phase 4A: Multi-group generation with V1 vocabulary mapping and validation.
Batch 2A: vocabulary-aware re-derivation, matchability enforcement and
consistency checking between the flat pattern label and the structured groups.
"""
import json
import logging

from pathforge.ast_engine.patterns import ALL_PATTERNS

logger = logging.getLogger(__name__)
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
    "forward_pointer_advance",     # Batch 1: same-direction two pointers
    "candidate_selection",         # Vocabulary Layer 2: greedy scalar candidate selection (loop form)
    "hash_lookup",                 # Vocabulary Layer 2: key->value mapping lookup
    "frequency_counting",          # Vocabulary Layer 2: occurrence tallies
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
        "required": ["hash_lookup"],
        "optional": [],
        "excluded": ["recursive_branching"],
        "note": (
            "Key->value mapping lookup maps to hash_lookup. recursion is "
            "excluded: a dict used as a recursion memo has the same "
            "construction + membership shape but belongs to "
            "recursive_branching, not lookup."
        ),
    },
    "hash_map_frequency": {
        "required": ["frequency_counting"],
        "optional": ["hash_lookup"],
        "excluded": ["recursive_branching"],
        "note": (
            "Occurrence tallying maps to frequency_counting, with a mapping "
            "lookup as optional support. recursion is excluded: a dict used as "
            "a memo has the same construction shape but is not a tally."
        ),
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
        "required": ["forward_pointer_advance"],
        "optional": [],
        "excluded": ["two_pointers_opposite"],
        "note": (
            "Same-direction two pointers map to forward_pointer_advance. "
            "bidirectional_index_scan is reserved for opposite-direction scans "
            "(it requires opposite_direction_updates) and cannot be produced "
            "by a same-direction implementation."
        ),
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
        "required": ["forward_pointer_advance"],
        "optional": [],
        "excluded": [],
        "note": (
            "Fast/slow pointers are same-direction progression and map to "
            "forward_pointer_advance (multiple_pointer_traversal evidence)."
        ),
    },
    "linked_list_reversal": {
        "required": ["linked_list_traversal"],
        "optional": [],
        "excluded": ["two_pointers_opposite"],
        "note": "Linked-list reversal maps to linked_list_traversal technique (requires pointer manipulation)",
    },
    "monotonic_stack": {
        "required": ["monotonic_stack_maintenance"],
        "optional": [],
        "excluded": [],
        "note": "Monotonic stack maps to monotonic_stack_maintenance technique",
    },
    "monotonic_deque": {
        "required": ["monotonic_stack_maintenance"],
        "optional": [],
        "excluded": [],
        "note": "Monotonic deque maps to monotonic_stack_maintenance technique (deque = stack variant)",
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
        "required": ["candidate_selection"],
        "optional": ["sequential_accumulation"],
        "excluded": ["sliding_window"],
        "note": (
            "Vocabulary Layer 2: greedy local decisions map to the "
            "candidate_selection technique, which has two structural forms: "
            "(1) loop + conditional branch + scalar candidate replacement, "
            "non-index participating; (2) sorting_operation + bounded read "
            "of the same sequence (extremum_access). sliding_window is "
            "excluded: conditionally-updated window state participates as a "
            "subscript index and is not candidate selection."
        ),
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


# ============================================================
# Batch 2A: matchability, vocabulary refresh and consistency
# ============================================================

# Legacy patterns that the current V1 vocabulary has no concept for. A group
# derived from one of these alone can never be satisfied, so it must be exposed
# as unmatchable rather than persisted as if it were a normal requirement.
MISSING_VOCABULARY_PATTERNS = frozenset(
    pattern
    for pattern, mapping in PATTERN_TO_V1_MAPPING.items()
    if not mapping.get("required")
)

# Provenance marker applied by _build_single_group. A group carrying it had its
# required/optional/excluded computed by the V1 vocabulary mapping at the time
# ground truth was generated, which means the concepts are reproducibly derived
# from the legacy patterns and may be re-derived when the mapping improves.
VOCABULARY_DERIVATION_MARKER = "vocabulary_v1"

# Provenance marker appended when a stored group's concepts are re-derived.
VOCABULARY_REFRESH_MARKER = "vocabulary_refresh"


def missing_vocabulary_for_patterns(patterns) -> list:
    """Return the legacy patterns that have no concept in the current vocabulary."""
    return sorted({p for p in (patterns or []) if p in MISSING_VOCABULARY_PATTERNS})


def _derive_concepts_from_patterns(patterns) -> tuple:
    """Apply the CURRENT mapping to legacy patterns, returning (required, excluded)."""
    required = set()
    excluded = set()
    for pattern in patterns or []:
        mapping = PATTERN_TO_V1_MAPPING.get(pattern)
        if not mapping:
            continue
        required.update(mapping.get("required", []))
        excluded.update(mapping.get("excluded", []))
    required -= excluded
    return sorted(required), sorted(excluded)


def pattern_family(pattern: str):
    """The solution family a legacy pattern belongs to, or None if unmapped.

    This is the single definition of "these two patterns are the same approach
    vs. different approaches" used by both the flat-pattern derivation
    (``_split_csv_patterns_to_groups``) and the stored-group vocabulary refresh.

    The family is the pattern's primary concept: the first strategy it maps to,
    or its first required concept when no strategy applies. Patterns sharing a
    family are merged into one solution group; patterns in different families
    are ALTERNATIVE approaches, never one conjunctive requirement.
    """
    mapping = PATTERN_TO_V1_MAPPING.get(pattern)
    if not mapping or not mapping.get("required"):
        return None
    for concept in mapping["required"]:
        if concept in VALID_STRATEGIES:
            return concept
    return mapping["required"][0]


def patterns_span_multiple_families(patterns) -> bool:
    """True when a pattern list contains more than one solution family.

    Such a list describes alternative approaches (approach A OR approach B).
    Collapsing it into a single group's ``required`` list makes a conjunction
    that no single implementation can satisfy, so callers must keep them as
    separate alternative groups.
    """
    families = {pattern_family(p) for p in (patterns or [])}
    families.discard(None)
    return len(families) > 1


def group_matchability(group: dict) -> tuple:
    """Decide whether a solution group can ever be satisfied.

    A group is matchable only when it carries at least one ``required`` concept.
    A group whose required list is empty is unsatisfiable by construction and
    must never be presented as a normal requirement. Returns (matchable, reason);
    the reason names the missing vocabulary instead of inventing a requirement.
    """
    if group.get("required"):
        return True, ""

    patterns = list(group.get("patterns") or [])
    if not patterns:
        return False, (
            "missing_vocabulary: group has no required concepts and no legacy "
            "patterns to derive them from"
        )

    missing = missing_vocabulary_for_patterns(patterns)
    if missing:
        return False, (
            "missing_vocabulary: the V1 vocabulary defines no concept for legacy "
            "pattern(s) " + ", ".join(missing)
        )

    return False, (
        "missing_vocabulary: no required concept could be derived from legacy "
        "pattern(s) " + ", ".join(sorted(patterns))
    )


def mark_group_matchability(group: dict) -> dict:
    """Annotate a group with its matchability, in place.

    Unmatchable groups keep their legacy patterns so the missing vocabulary is
    visible to callers, but are explicitly flagged so they are never persisted
    or emitted as a satisifiable requirement.
    """
    matchable, reason = group_matchability(group)
    group["matchable"] = matchable
    if matchable:
        group.pop("matchability_reason", None)
    else:
        group["validation"] = "unmatchable"
        group["matchability_reason"] = reason
    return group


def refresh_group_vocabulary(group: dict, sibling_requirements: dict) -> bool:
    """Re-derive a vocabulary-derived group's concepts from its own patterns.

    Stored groups keep the ``required`` list that the mapping produced when they
    were generated. When the vocabulary improves, those concepts can be stale
    and permanently unsatisfiable, so they are recomputed here from the group's
    own legacy patterns using the current mapping.

    Skipped when:
    - the group was not derived by the vocabulary mapping (curated concepts),
    - the group has no legacy patterns, or has patterns outside the mapping,
    - sibling groups share the same patterns but require different concepts:
      that difference is curated information the mapping cannot reproduce.

    Returns True when the group changed.
    """
    provenance = list(group.get("provenance") or [])
    if VOCABULARY_DERIVATION_MARKER not in provenance:
        return False

    patterns = list(group.get("patterns") or [])
    if not patterns:
        return False
    if any(pattern not in PATTERN_TO_V1_MAPPING for pattern in patterns):
        return False

    # Alternative approaches must never be collapsed into one conjunctive
    # requirement by the refresh. Multi-family groups are expanded into
    # separate alternative groups by the loader instead.
    if patterns_span_multiple_families(patterns):
        return False

    key = tuple(sorted(patterns))
    if len(sibling_requirements.get(key, set())) > 1:
        return False

    required, excluded = _derive_concepts_from_patterns(patterns)
    if sorted(group.get("required") or []) == required and \
            sorted(group.get("excluded") or []) == excluded:
        return False

    group["required"] = required
    group["excluded"] = excluded
    group["optional"] = sorted(
        set(group.get("optional") or []) - set(required) - set(excluded)
    )
    if VOCABULARY_REFRESH_MARKER not in provenance:
        provenance.append(VOCABULARY_REFRESH_MARKER)
    group["provenance"] = provenance
    return True


def refresh_groups_vocabulary(groups: list) -> list:
    """Refresh every stale vocabulary-derived group. Returns the changed group ids."""
    sibling_requirements = {}
    for group in groups or []:
        key = tuple(sorted(group.get("patterns") or []))
        sibling_requirements.setdefault(key, set()).add(
            tuple(sorted(group.get("required") or []))
        )

    refreshed = []
    for group in groups or []:
        if refresh_group_vocabulary(group, sibling_requirements):
            refreshed.append(group.get("id", ""))
    return refreshed


def find_ground_truth_disagreements(patterns, groups) -> list:
    """Detect drift between the flat pattern label and structured solution groups.

    ``problems.pattern`` (and the legacy flat list) is one representation of the
    accepted approaches; the structured groups are another. They are allowed to
    describe the same set of approaches, but they must not silently disagree.
    Returns a list of structured findings, each with a ``kind``:

    - ``pattern_not_in_groups``: a declared pattern no group covers.
    - ``group_pattern_not_declared``: a group pattern the flat label omits.
    - ``concept_not_derived_from_patterns``: a group requires a concept the
      mapping cannot derive from the patterns those concepts came from (e.g.
      alternative groups that the flat label cannot express).

    The concept check compares against ``derivation_patterns`` when present —
    reconciliation deliberately lets a curated pattern label override the
    production patterns, so the label alone cannot judge derivability.
    - ``unmatchable_group``: the group has no required concept at all.
    """
    declared = list(patterns or [])
    declared_set = set(declared)

    group_patterns = set()
    for group in groups or []:
        group_patterns.update(group.get("patterns") or [])

    findings = []

    for pattern in sorted(declared_set - group_patterns):
        findings.append({
            "kind": "pattern_not_in_groups",
            "pattern": pattern,
            "detail": f"declared pattern '{pattern}' is not covered by any solution group",
        })

    for pattern in sorted(group_patterns - declared_set):
        findings.append({
            "kind": "group_pattern_not_declared",
            "pattern": pattern,
            "detail": f"solution group pattern '{pattern}' is not in the declared pattern list",
        })

    for group in groups or []:
        group_id = group.get("id", "")
        required = list(group.get("required") or [])

        if not required:
            _, reason = group_matchability(group)
            findings.append({
                "kind": "unmatchable_group",
                "group_id": group_id,
                "patterns": list(group.get("patterns") or []),
                "detail": reason,
            })
            continue

        source_patterns = list(
            group.get("derivation_patterns") or group.get("patterns") or []
        )
        if not source_patterns or any(
            p not in PATTERN_TO_V1_MAPPING for p in source_patterns
        ):
            # Concepts were not derived from a recognised legacy pattern set,
            # so derivability cannot be judged. Not a drift finding.
            continue

        derivable, _ = _derive_concepts_from_patterns(source_patterns)
        derivable_set = set(derivable)
        for concept in sorted(set(required) - derivable_set):
            findings.append({
                "kind": "concept_not_derived_from_patterns",
                "group_id": group_id,
                "concept": concept,
                "derivable_concepts": sorted(derivable_set),
                "patterns": list(group.get("patterns") or []),
                "detail": (
                    f"group '{group_id}' requires '{concept}', which the current "
                    f"vocabulary cannot derive from its patterns {source_patterns}"
                ),
            })

    return findings


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

    # Batch 2A: a group with no required concept cannot be satisfied. Expose the
    # missing vocabulary instead of letting an unsatisfiable group look normal.
    for group in validated_groups:
        mark_group_matchability(group)

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
            VOCABULARY_DERIVATION_MARKER,
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

    # Group patterns by solution family (their primary concept), using the same
    # shared definition every other derivation path uses.
    strategy_groups = {}
    unmapped = []

    for pattern in patterns:
        family = pattern_family(pattern)
        if family is not None:
            strategy_groups.setdefault(family, []).append(pattern)
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

    # Batch 2A: never persist an unsatisfiable group. Groups whose legacy
    # patterns have no concept in the current vocabulary are dropped here and
    # the missing vocabulary is named, so the gap is visible instead of being
    # stored as a matchable requirement that can never be satisfied.
    persistable_groups = [g for g in solution_groups if g.get("matchable", True)]
    unmatchable_groups = [g for g in solution_groups if not g.get("matchable", True)]
    if unmatchable_groups:
        missing_vocabulary = sorted({
            p
            for g in unmatchable_groups
            for p in (g.get("patterns") or [])
            if p in MISSING_VOCABULARY_PATTERNS
        })
        logger.warning(
            "Ground truth for problem %d has no matchable concept for legacy "
            "pattern(s) %s; %d unsatisfiable group(s) were not persisted. "
            "Patterns=%s",
            problem_id,
            missing_vocabulary or "(undetermined)",
            len(unmatchable_groups),
            patterns,
        )

    solution_groups_json = json.dumps(persistable_groups)

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
