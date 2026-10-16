"""Error analysis and localization for the evaluation benchmark.

For every false positive and false negative, classify the source of failure.
Produces error_analysis.csv with per-error localization.
"""

import csv
import json
import os
import sys
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ── Error type definitions ──────────────────────────────────────────────

ERROR_TYPES = {
    "PARSER_FAILURE": "Code could not be parsed into AST",
    "STRUCTURAL_FACT_FAILURE": "Structural facts were not extracted correctly",
    "TECHNIQUE_DETECTION_FAILURE": "Technique detection failed despite facts being present",
    "STRATEGY_INFERENCE_FAILURE": "Strategy inference failed despite techniques being present",
    "SOLUTION_GROUP_MATCHING_FAILURE": "Solution-group matching produced wrong outcome",
    "CONFIDENCE_FAILURE": "Detection present but confidence too low for classification",
    "GROUND_TRUTH_AMBIGUITY": "Ground truth label is uncertain or debatable",
    "NAMING_DEPENDENCY": "Detection depends on variable names rather than structure",
    "FALSE_POSITIVE_SYSTEMATIC": "Detector fires on patterns that are not the target concept",
    "MISSING_DETECTOR": "No detector exists for this concept in this system",
    "UNKNOWN": "Failure cause unclear",
}


def classify_legacy_error(
    submission: dict,
    detected_concepts: set,
    target_concepts: list,
    ground_truth: dict = None,
) -> str:
    """Classify the error type for a legacy analysis false positive/negative."""
    legacy = submission.get("legacy", {})
    
    # Parser failure
    if not legacy.get("success"):
        error_type = legacy.get("error_type", "")
        if "Syntax" in error_type:
            return "PARSER_FAILURE"
        return "PARSER_FAILURE"
    
    # Missing detector
    if not target_concepts:
        return "MISSING_DETECTOR"
    
    # Check if the concept has a legacy detector
    concept_has_detector = {
        "hash_map_lookup": True,
        "hash_map_frequency": True,
        "prefix_sum": True,
        "sliding_window_fixed": True,
        "sliding_window_variable": True,
        "two_pointers_opposite": True,
        "two_pointers_same": True,
        "dfs_recursive": True,
        "dfs_iterative": True,
        "bfs_level_order": True,
        "bfs_shortest_path": True,
        "topological_sort": True,
        "union_find": True,
        "binary_search_tree": True,
        "dp_1d_forward": True,
        "dp_1d_sequence": True,
        "dp_2d_grid": True,
        "dp_2d_string": True,
        "dp_knapsack": True,
        "dp_interval": True,
        "dp_state_machine": True,
        "fast_slow_pointers": True,
        "linked_list_reversal": True,
        "monotonic_stack": True,
        "monotonic_deque": True,
        "binary_search_standard": True,
        "binary_search_rotated": True,
        "binary_search_answer": True,
        "heap_top_k": True,
        "greedy_local": True,
        "greedy_interval": True,
        "backtracking_permutation": True,
        "backtracking_subset": True,
    }
    
    for concept in target_concepts:
        if concept not in concept_has_detector or not concept_has_detector[concept]:
            return "MISSING_DETECTOR"
    
    # Check patterns detected
    patterns = legacy.get("detected_patterns", [])
    
    # False positive: detected something not in target
    for detected in detected_concepts:
        if detected not in target_concepts:
            return "FALSE_POSITIVE_SYSTEMATIC"
    
    # False negative: target not detected
    for concept in target_concepts:
        if concept not in detected_concepts:
            # Check if any pattern has low confidence
            for p in patterns:
                if p.get("pattern_id") == concept:
                    conf = p.get("confidence", 0.0)
                    if 0.0 < conf < 0.5:
                        return "CONFIDENCE_FAILURE"
            
            return "UNKNOWN"
    
    return "UNKNOWN"


def classify_shadow_error(
    submission: dict,
    detected_concepts: set,
    target_concepts: list,
    ground_truth: dict = None,
) -> str:
    """Classify the error type for a shadow analysis false positive/negative."""
    shadow = submission.get("shadow", {})
    
    # Shadow returned None (parse failure or exception)
    if not shadow.get("success"):
        error_type = shadow.get("error_type", "")
        if error_type == "SHADOW_RETURNED_NONE":
            return "PARSER_FAILURE"
        if "Syntax" in error_type:
            return "PARSER_FAILURE"
        return "PARSER_FAILURE"
    
    # Check structural facts
    facts = shadow.get("structural_facts", [])
    techniques = shadow.get("technique_evidence", [])
    strategies = shadow.get("strategy_evidence", [])
    
    # No facts extracted
    if not facts:
        return "STRUCTURAL_FACT_FAILURE"
    
    # Facts present but no techniques
    if facts and not techniques:
        return "TECHNIQUE_DETECTION_FAILURE"
    
    # Techniques present but no strategies
    if techniques and not strategies:
        return "STRATEGY_INFERENCE_FAILURE"
    
    # Check for naming dependencies in shadow
    for tech in techniques:
        fact_ids = tech.get("supporting_fact_ids", [])
        for fid in fact_ids:
            for fact in facts:
                if fact.get("fact_id") == fid:
                    attrs = fact.get("attributes", {})
                    # Check if detection depends on variable names
                    for key in ["variable", "cache_variable", "graph_variable",
                               "queue_variable", "structure"]:
                        val = attrs.get(key, "")
                        if val and val.lower() in {
                            "cache", "memo", "dp", "table", "visited", "seen",
                            "graph", "adj", "queue", "q", "bfs_queue",
                        }:
                            return "NAMING_DEPENDENCY"
    
    return "UNKNOWN"


def run_error_analysis(
    raw_results_path: str,
    ground_truth_path: str,
    output_dir: str,
) -> dict:
    """Run error analysis on all submissions."""
    os.makedirs(output_dir, exist_ok=True)
    
    with open(raw_results_path, 'r', encoding='utf-8') as f:
        raw_results = json.load(f)
    
    ground_truth = {}
    if os.path.exists(ground_truth_path):
        with open(ground_truth_path, 'r', encoding='utf-8') as f:
            gt_list = json.load(f)
        ground_truth = {gt["submission_id"]: gt for gt in gt_list}
    
    # Use target_concepts as ground truth proxy if no explicit labels
    if not ground_truth:
        for result in raw_results:
            gt_entry = {
                "submission_id": result["submission_id"],
                "present": result.get("target_concepts", []),
                "absent": [],
                "uncertain": [],
            }
            ground_truth[result["submission_id"]] = gt_entry
    
    errors = []
    error_summary = {
        "legacy": defaultdict(int),
        "shadow": defaultdict(int),
    }
    
    for result in raw_results:
        sub_id = result["submission_id"]
        gt = ground_truth.get(sub_id, {})
        target = set(gt.get("present", []))
        
        # Legacy analysis
        legacy = result.get("legacy", {})
        if legacy.get("success"):
            detected_legacy = set()
            for p in legacy.get("detected_patterns", []):
                if p.get("detected", False) and p.get("confidence", 0.0) > 0.0:
                    detected_legacy.add(p.get("pattern_id", ""))
        else:
            detected_legacy = set()
        
        # False negatives for legacy
        for concept in target:
            if concept not in detected_legacy:
                error_type = classify_legacy_error(result, detected_legacy, [concept], gt)
                errors.append({
                    "submission_id": sub_id,
                    "concept": concept,
                    "error_type": error_type,
                    "system": "legacy",
                    "result": "false_negative",
                    "probable_failure_layer": _get_failure_layer(error_type),
                    "short_explanation": ERROR_TYPES.get(error_type, "Unknown"),
                })
                error_summary["legacy"][error_type] += 1
        
        # False positives for legacy
        for concept in detected_legacy:
            if concept not in target and concept not in gt.get("uncertain", []):
                error_type = classify_legacy_error(result, detected_legacy, [concept], gt)
                errors.append({
                    "submission_id": sub_id,
                    "concept": concept,
                    "error_type": error_type,
                    "system": "legacy",
                    "result": "false_positive",
                    "probable_failure_layer": _get_failure_layer(error_type),
                    "short_explanation": ERROR_TYPES.get(error_type, "Unknown"),
                })
                error_summary["legacy"][error_type] += 1
        
        # Shadow analysis
        shadow = result.get("shadow", {})
        if shadow.get("success"):
            detected_shadow = set()
            for tech in shadow.get("technique_evidence", []):
                detected_shadow.add(tech.get("technique_id", ""))
            for strat in shadow.get("strategy_evidence", []):
                detected_shadow.add(strat.get("strategy_id", ""))
        else:
            detected_shadow = set()
        
        # False negatives for shadow
        for concept in target:
            # Map target concept to shadow equivalent
            shadow_concept = _map_to_shadow_concept(concept)
            if shadow_concept not in detected_shadow and concept not in detected_shadow:
                error_type = classify_shadow_error(result, detected_shadow, [concept], gt)
                errors.append({
                    "submission_id": sub_id,
                    "concept": concept,
                    "error_type": error_type,
                    "system": "shadow",
                    "result": "false_negative",
                    "probable_failure_layer": _get_failure_layer(error_type),
                    "short_explanation": ERROR_TYPES.get(error_type, "Unknown"),
                })
                error_summary["shadow"][error_type] += 1
        
        # False positives for shadow
        for concept in detected_shadow:
            original = _map_from_shadow_concept(concept)
            if original not in target and concept not in target:
                error_type = classify_shadow_error(result, detected_shadow, [concept], gt)
                errors.append({
                    "submission_id": sub_id,
                    "concept": concept,
                    "error_type": error_type,
                    "system": "shadow",
                    "result": "false_positive",
                    "probable_failure_layer": _get_failure_layer(error_type),
                    "short_explanation": ERROR_TYPES.get(error_type, "Unknown"),
                })
                error_summary["shadow"][error_type] += 1
    
    # Save error analysis CSV
    csv_path = os.path.join(output_dir, "error_analysis.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "submission_id", "concept", "error_type", "system", "result",
            "probable_failure_layer", "short_explanation"
        ])
        writer.writeheader()
        writer.writerows(errors)
    
    # Save error summary
    summary = {
        "total_errors": len(errors),
        "legacy_errors": dict(error_summary["legacy"]),
        "shadow_errors": dict(error_summary["shadow"]),
        "legacy_total": sum(error_summary["legacy"].values()),
        "shadow_total": sum(error_summary["shadow"].values()),
    }
    
    with open(os.path.join(output_dir, "error_summary.json"), 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Print summary
    print(f"\nError Analysis Summary:")
    print(f"  Total errors: {summary['total_errors']}")
    print(f"  Legacy errors: {summary['legacy_total']}")
    for et, count in sorted(error_summary["legacy"].items()):
        print(f"    {et}: {count}")
    print(f"  Shadow errors: {summary['shadow_total']}")
    for et, count in sorted(error_summary["shadow"].items()):
        print(f"    {et}: {count}")
    
    return summary


def _get_failure_layer(error_type: str) -> str:
    """Map error type to pipeline layer."""
    mapping = {
        "PARSER_FAILURE": "parsing",
        "STRUCTURAL_FACT_FAILURE": "structural_fact_extraction",
        "TECHNIQUE_DETECTION_FAILURE": "technique_detection",
        "STRATEGY_INFERENCE_FAILURE": "strategy_inference",
        "SOLUTION_GROUP_MATCHING_FAILURE": "solution_group_matching",
        "CONFIDENCE_FAILURE": "confidence_scoring",
        "GROUND_TRUTH_AMBIGUITY": "ground_truth",
        "NAMING_DEPENDENCY": "structural_fact_extraction",
        "FALSE_POSITIVE_SYSTEMATIC": "detection_logic",
        "MISSING_DETECTOR": "architecture_gap",
        "UNKNOWN": "unknown",
    }
    return mapping.get(error_type, "unknown")


def _map_to_shadow_concept(concept: str) -> str:
    """Map legacy concept to shadow equivalent."""
    mapping = {
        "sliding_window_fixed": "fixed_window_maintenance",
        "sliding_window_variable": "loop_state_tracking",
        "two_pointers_opposite": "bidirectional_index_scan",
        "binary_search_standard": "binary_search",
        "monotonic_stack": "monotonic_stack_maintenance",
        "union_find": "union_find",
        "dfs_recursive": "recursive_branching",
        "bfs_shortest_path": "bfs_shortest_path",
        "backtracking_permutation": "dfs_backtracking",
        "backtracking_subset": "dfs_backtracking",
    }
    return mapping.get(concept, concept)


def _map_from_shadow_concept(shadow_concept: str) -> str:
    """Map shadow concept back to legacy equivalent."""
    reverse = {
        "fixed_window_maintenance": "sliding_window_fixed",
        "loop_state_tracking": "sliding_window_variable",
        "bidirectional_index_scan": "two_pointers_opposite",
        "binary_search": "binary_search_standard",
        "monotonic_stack_maintenance": "monotonic_stack",
        "union_find": "union_find",
        "recursive_branching": "dfs_recursive",
        "bfs_shortest_path": "bfs_shortest_path",
        "dfs_backtracking": "backtracking_permutation",
        "sequential_accumulation": "sequential_accumulation",
        "carry_propagation": "carry_propagation",
        "iterative_table_filling": "iterative_table_filling",
        "linked_list_traversal": "linked_list_traversal",
        "dp_top_down": "dp_top_down",
        "dp_bottom_up": "dp_bottom_up",
        "two_pointers_opposite": "two_pointers_opposite",
        "sliding_window": "sliding_window_variable",
    }
    return reverse.get(shadow_concept, shadow_concept)


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    raw_results = str(base_dir / "results" / "raw_outputs" / "raw_results.json")
    ground_truth = str(base_dir / "ground_truth" / "labels.json")
    output_dir = str(base_dir / "results" / "error_analysis")
    
    if not os.path.exists(raw_results):
        print("Raw results not found. Please run run_evaluation.py first.")
        sys.exit(1)
    
    run_error_analysis(raw_results, ground_truth, output_dir)
