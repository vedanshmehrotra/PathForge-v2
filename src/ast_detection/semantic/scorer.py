"""Rule-based pattern scorer using semantic features.

Computes deterministic, explainable confidence scores for algorithmic patterns
based on extracted semantic features. Scores are in range [0.0, 1.0].
"""
from dataclasses import dataclass, field
from typing import Dict, List

from .features import SemanticFeatures


@dataclass
class ScoreEvidence:
    """Evidence for a pattern score."""
    feature: str
    weight: float
    description: str


@dataclass
class PatternScore:
    """Score and evidence for a single pattern."""
    pattern: str
    score: float
    evidence: List[ScoreEvidence] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pattern": self.pattern,
            "score": round(self.score, 4),
            "evidence": [
                {"feature": e.feature, "weight": e.weight, "description": e.description}
                for e in self.evidence
            ],
        }


def score_patterns(features: SemanticFeatures) -> Dict[str, PatternScore]:
    """Compute pattern scores from semantic features.

    Args:
        features: Extracted semantic features

    Returns:
        Dict mapping pattern name to PatternScore
    """
    scores = {}
    scores["array_traversal"] = _score_array_traversal(features)
    scores["hash_map_lookup"] = _score_hash_map_lookup(features)
    scores["prefix_sum"] = _score_prefix_sum(features)
    scores["two_pointers_opposite"] = _score_two_pointers_opposite(features)

    # Apply mutual exclusion rules
    scores = _apply_mutual_exclusion(scores, features)

    return scores


# ===========================================================================
# Fix 1: array_traversal — recognize for-loop counters and enumerate
# ===========================================================================

def _score_array_traversal(features: SemanticFeatures) -> PatternScore:
    """Score array_traversal pattern.

    Evidence: counter loop (while or for) + indexed access + sequential index
    movement. For-loop counters and enumerate get equivalent weight to
    while-loop counters.
    """
    score = 0.0
    evidence = []

    # Fix 1: for-loop counter and while-loop counter are equivalent evidence
    if features.loops.has_counter_loop:
        if features.loops.has_for_counter_loop:
            w = 0.30
            score += w
            evidence.append(ScoreEvidence(
                "for_counter_loop", w,
                f"For-loop counter with variable '{features.loops.counter_var}'",
            ))
        else:
            w = 0.30
            score += w
            evidence.append(ScoreEvidence(
                "counter_loop", w,
                f"While-loop counter with variable '{features.loops.counter_var}'",
            ))

    if features.access.has_indexed_access:
        w = 0.25
        score += w
        evidence.append(ScoreEvidence(
            "indexed_access", w,
            f"Indexed access to '{features.access.indexed_collection}'",
        ))

    if features.access.has_sequential_index:
        w = 0.20
        score += w
        evidence.append(ScoreEvidence(
            "sequential_index", w,
            "Sequential index access (e.g., arr[i], arr[i-1])",
        ))

    if features.pointers.has_index_movement:
        w = 0.15
        score += w
        evidence.append(ScoreEvidence(
            "index_movement", w,
            f"Index variable '{features.pointers.movement_var}' advances by {features.pointers.movement_step}",
        ))

    if features.loops.counter_compares_to_len:
        w = 0.10
        score += w
        evidence.append(ScoreEvidence(
            "bound_comparison", w,
            "Loop bound compared to len()",
        ))

    # enumerate gives strong traversal evidence even without explicit counter
    if features.loops.has_enumerate_iteration:
        w = 0.15
        score += w
        evidence.append(ScoreEvidence(
            "enumerate_iteration", w,
            "enumerate() iteration over collection",
        ))

    # Direct collection iteration (for x in arr) without counter loop
    if features.loops.has_collection_iteration and not features.loops.has_counter_loop:
        # With indexed access: moderate evidence
        if (features.access.has_indexed_access
                and features.access.indexed_collection == features.loops.collection_var):
            w = 0.15
            score += w
            evidence.append(ScoreEvidence(
                "iteration_with_indexing", w,
                f"Iteration and indexed access on '{features.loops.collection_var}'",
            ))
        # With accumulation: moderate evidence (e.g., for x in arr: total += x)
        elif features.accumulation.has_accumulation:
            w = 0.20
            score += w
            evidence.append(ScoreEvidence(
                "iteration_with_accumulation", w,
                f"Collection iteration with accumulation on '{features.loops.collection_var}'",
            ))
        # With append: moderate evidence (e.g., for x in arr: result.append(x))
        elif features.accumulation.has_append_accumulation:
            w = 0.20
            score += w
            evidence.append(ScoreEvidence(
                "iteration_with_append", w,
                f"Collection iteration with append on '{features.loops.collection_var}'",
            ))

    return PatternScore("array_traversal", min(score, 1.0), evidence)


# ===========================================================================
# Fix 2: hash_map_lookup — distinguish dict/set membership from list membership
# ===========================================================================

def _score_hash_map_lookup(features: SemanticFeatures) -> PatternScore:
    """Score hash_map_lookup pattern.

    Strong evidence: membership test on a known dict or set variable.
    Weak evidence: membership test on unknown collection.
    Penalty: membership test on same collection that is indexed (likely list).
    """
    score = 0.0
    evidence = []

    if features.access.has_membership_test:
        # Fix 2: Check if membership is on a known hash collection
        if features.access.membership_on_hash_collection:
            w = 0.65
            score += w
            coll_type = features.access.membership_collection_type
            evidence.append(ScoreEvidence(
                "hash_membership", w,
                f"Membership test on {coll_type} variable '{features.access.membership_collection}'",
            ))
        else:
            # Unknown or list collection — weak evidence
            w = 0.15
            score += w
            evidence.append(ScoreEvidence(
                "membership_test_weak", w,
                f"Membership test on '{features.access.membership_collection}' (collection type unknown)",
            ))

        # Penalty: same collection is indexed → likely a list
        if (features.access.has_indexed_access and
                features.access.indexed_collection == features.access.membership_collection):
            penalty = -0.20
            score += penalty
            evidence.append(ScoreEvidence(
                "list_likely_penalty", penalty,
                "Collection is also indexed, strongly suggesting list (linear search)",
            ))

    # Bonus: dict construction + membership = strong hash map signal
    if features.access.dict_vars and features.access.has_membership_test:
        w = 0.15
        score += w
        evidence.append(ScoreEvidence(
            "dict_constructed", w,
            f"Dict construction detected: {', '.join(features.access.dict_vars)}",
        ))

    # Bonus: set construction + membership = strong hash set signal
    if features.access.set_vars and features.access.has_membership_test:
        w = 0.15
        score += w
        evidence.append(ScoreEvidence(
            "set_constructed", w,
            f"Set construction detected: {', '.join(features.access.set_vars)}",
        ))

    # --- Dict .get() lookup (membership-equivalent) ---
    # .get() is a hash-based lookup even though it doesn't use `in`.
    if features.access.has_dict_get_lookup and features.access.dict_vars:
        w = 0.50
        score += w
        evidence.append(ScoreEvidence(
            "dict_get_lookup", w,
            f"Dict .get() lookup detected on: {', '.join(features.access.dict_vars)}",
        ))

    # Note: dict construction alone (seen[item] = True) is NOT hash_map_lookup.
    # Only explicit membership tests, .get() calls, or .items()/keys() qualify.

    return PatternScore("hash_map_lookup", max(min(score, 1.0), 0.0), evidence)


# ===========================================================================
# Fix 3: prefix_sum — require numeric accumulation from collection
# ===========================================================================

def _score_prefix_sum(features: SemanticFeatures) -> PatternScore:
    """Score prefix_sum pattern.

    Strong evidence: numeric accumulation from collection elements.
    Weak evidence: generic accumulator without collection access.
    Penalty: non-numeric accumulation (string concat, counter).
    """
    score = 0.0
    evidence = []

    if features.accumulation.has_accumulation:
        # Fix 3: Check if accumulation is numeric
        if features.accumulation.has_numeric_accumulation:
            w = 0.30
            score += w
            evidence.append(ScoreEvidence(
                "numeric_accumulation", w,
                f"Numeric accumulation: {features.accumulation.accumulator_var} {features.accumulation.accumulator_op} {features.accumulation.accumulator_source}",
            ))
        else:
            # Non-numeric accumulation — zero evidence for prefix_sum
            w = 0.00
            score += w
            evidence.append(ScoreEvidence(
                "non_numeric_accumulation", w,
                f"Non-numeric accumulation: {features.accumulation.accumulator_var} {features.accumulation.accumulator_op} {features.accumulation.accumulator_source}",
            ))

    if features.accumulation.has_running_sum:
        w = 0.30
        score += w
        evidence.append(ScoreEvidence(
            "running_sum", w,
            "Accumulating values from a collection (running sum)",
        ))

    if features.loops.has_counter_loop:
        w = 0.15
        score += w
        evidence.append(ScoreEvidence(
            "counter_loop", w,
            "Accumulation inside a counter loop",
        ))

    if features.access.has_indexed_access:
        w = 0.10
        score += w
        evidence.append(ScoreEvidence(
            "indexed_access", w,
            "Collection accessed by index during accumulation",
        ))

    # Bonus: accumulator is from collection elements (stronger signal)
    if features.accumulation.accumulator_is_from_collection:
        w = 0.15
        score += w
        evidence.append(ScoreEvidence(
            "collection_accumulation", w,
            "Accumulator receives values directly from collection elements",
        ))

    # Fix 3: append accumulation (e.g., prefix.append(prefix[-1] + num))
    if features.accumulation.has_append_accumulation:
        w = 0.25
        score += w
        evidence.append(ScoreEvidence(
            "append_accumulation", w,
            f"Append with self-referencing value: {features.accumulation.accumulator_source}",
        ))

    # Fix 4: assignment accumulation (e.g., prefix[i] = prefix[i-1] + arr[i-1])
    if features.accumulation.has_assignment_accumulation:
        w = 0.25
        score += w
        evidence.append(ScoreEvidence(
            "assignment_accumulation", w,
            f"Prefix recurrence: {features.accumulation.accumulator_source}",
        ))

    return PatternScore("prefix_sum", min(score, 1.0), evidence)


# ===========================================================================
# two_pointers_opposite (unchanged)
# ===========================================================================

def _score_two_pointers_opposite(features: SemanticFeatures) -> PatternScore:
    """Score two_pointers_opposite pattern.

    Evidence: two variables moving toward each other (bidirectional).
    """
    score = 0.0
    evidence = []

    if features.pointers.has_index_movement and features.pointers.has_bidirectional:
        w = 0.50
        score += w
        evidence.append(ScoreEvidence(
            "bidirectional_movement", w,
            "Two variables moving in opposite directions",
        ))

    if features.loops.has_counter_loop and not features.pointers.has_bidirectional:
        penalty = -0.20
        score += penalty
        evidence.append(ScoreEvidence(
            "single_counter", penalty,
            "Only one counter variable detected (not two pointers)",
        ))

    return PatternScore("two_pointers_opposite", max(min(score, 1.0), 0.0), evidence)


# ===========================================================================
# Mutual exclusion rules
# ===========================================================================

def _apply_mutual_exclusion(scores: Dict[str, PatternScore], features: SemanticFeatures) -> Dict[str, PatternScore]:
    """Apply mutual exclusion rules to reduce false positives."""
    # If bidirectional movement is detected, reduce array_traversal and prefix_sum
    if features.pointers.has_bidirectional:
        if "array_traversal" in scores:
            scores["array_traversal"].score *= 0.5
            scores["array_traversal"].evidence.append(ScoreEvidence(
                "bidirectional_penalty", -0.5,
                "Reduced because bidirectional movement detected (not sequential traversal)",
            ))
        if "prefix_sum" in scores:
            scores["prefix_sum"].score *= 0.3
            scores["prefix_sum"].evidence.append(ScoreEvidence(
                "bidirectional_penalty", -0.7,
                "Reduced because bidirectional movement detected (not accumulation)",
            ))

    return scores
