"""gt_poc_v2 core primitives.

Re-exports the frozen comparison primitives from POC v1 (the same read-only
observation over the frozen shadow analyzer) and adds the V2 §1.5 coarse
structural profile.

The profile is derived ONLY from facts the frozen analyzer already emits plus a
bounded AST loop-nesting feature.  No edit distance, no embeddings, no new
structural facts.

Determinism: every function is a pure function of its inputs.  No timestamps,
no randomness, no network, no database.
"""
import ast

from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.relations import build_relations

# Reuse the v1 comparison primitives verbatim (single source of truth).
from experiments.code_analysis_evaluation.gt_poc.core import (  # noqa: F401
    PIPELINE_VERSION,
    analyze,
    canonicalized_source,
    fact_signature,
    levenshtein,
    sha256_hex,
    signature_class,
    skeleton_distance,
    skeleton_for,
    skeleton_tokens,
    strategy_ids,
    technique_ids,
)

from .problem_metadata import PEC_CONCEPTS, PEC_STRATEGIES, PEC_TECHNIQUES, SUPPORT_TECHNIQUES


# ---------------------------------------------------------------------------
# S1 — concept tiers
# ---------------------------------------------------------------------------

def concept_tier(concept: str) -> str:
    """Return 'PEC' or 'SUPPORT' for a concept id.

    An id in neither registry defaults to SUPPORT (safe default: new vocabulary
    cannot silently fragment families).  The POC records every defaulted id so
    the fallback is auditable rather than silent.
    """
    if concept in PEC_STRATEGIES or concept in PEC_TECHNIQUES:
        return "PEC"
    return "SUPPORT"


def classify_concepts(concepts) -> dict:
    """Partition a concept iterable into {'PEC': [...], 'SUPPORT': [...]}."""
    pec, support, tier_map = [], [], {}
    for c in sorted(set(concepts)):
        tier = concept_tier(c)
        tier_map[c] = tier
        (pec if tier == "PEC" else support).append(c)
    return {"PEC": pec, "SUPPORT": support, "tiers": tier_map}


def unknown_concepts(concepts) -> list:
    """Concept ids that are not explicitly registered in either tier set."""
    return sorted(
        c for c in set(concepts)
        if c not in PEC_CONCEPTS and c not in SUPPORT_TECHNIQUES
    )


# ---------------------------------------------------------------------------
# S3 — coarse structural profile (V2 §1.5)
# ---------------------------------------------------------------------------

def _max_loop_depth(node: ast.AST, depth: int = 0) -> int:
    """Maximum nesting depth of loop nodes (For/While) in the subtree."""
    best = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.For, ast.AsyncFor, ast.While)):
            best = max(best, _max_loop_depth(child, depth + 1))
        else:
            best = max(best, _max_loop_depth(child, depth))
    return best


def _iter_kind(iter_node) -> str:
    """Classify a for-loop iterable as 'range' or 'container'.

    ``range(len(x))`` is container-index iteration, not plain range counting, so
    it is classified as 'container' — this keeps ``enumerate(nums)`` and
    ``range(len(nums))`` in the same profile bucket for the same algorithm.
    """
    if (
        isinstance(iter_node, ast.Call)
        and isinstance(iter_node.func, ast.Name)
        and iter_node.func.id == "range"
    ):
        for arg in iter_node.args:
            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "len":
                return "container"
            if isinstance(arg, ast.Attribute) and arg.attr == "__len__":  # pragma: no cover
                return "container"
        return "range"
    return "container"


def compute_profile(code_text: str) -> dict:
    """Compute the five-dimensional V2 §1.5 profile for one solution."""
    tree = ast.parse(code_text)
    facts = extract_structural_facts(tree)
    rel = build_relations(tree)
    fact_types = {f.fact_type for f in facts}

    # recursion
    if "multiple_recursive_paths" in fact_types:
        recursion = "multi"
    elif "recursive_call_in_conditional" in fact_types or "self_recursive_call" in fact_types:
        recursion = "single"
    else:
        recursion = "none"

    # loop_shape (bounded nesting feature from the AST)
    depth = _max_loop_depth(tree)
    loop_shape = "none" if depth == 0 else ("flat" if depth == 1 else "nested")

    # container discipline
    has_append = any("append" in ops for ops in rel.collection_ops.values())
    if has_append:
        container = "append"
    elif "indexed_write" in fact_types:
        container = "index_write"
    elif "subscript_index_access" in fact_types or "subscript_read" in fact_types:
        container = "index_read"
    else:
        container = "none"

    # map_kind
    map_kinds = {
        f.attributes.get("kind")
        for f in facts
        if f.fact_type == "mapping_construction"
    }
    if map_kinds:
        map_kind = "dict"
    elif "list_construction" in fact_types:
        map_kind = "array_presized"
    else:
        map_kind = "none"

    # iterates_collection
    kinds = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.For, ast.AsyncFor)):
            kinds.add(_iter_kind(n.iter))
    if not kinds:
        iterates_collection = "none"
    elif len(kinds) == 1:
        iterates_collection = next(iter(kinds))
    else:
        iterates_collection = "both"

    return {
        "recursion": recursion,
        "loop_shape": loop_shape,
        "container": container,
        "map_kind": map_kind,
        "iterates_collection": iterates_collection,
        "_loop_depth": depth,
    }


PROFILE_DIMENSIONS = (
    "recursion", "loop_shape", "container", "map_kind", "iterates_collection",
)


def profile_tuple(profile: dict) -> tuple:
    """The five dimensions as a stable tuple (excludes diagnostic fields)."""
    return tuple(profile[d] for d in PROFILE_DIMENSIONS)
