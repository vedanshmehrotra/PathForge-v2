"""Calculate evaluation metrics from raw analysis results.

Compares detected concepts against ground truth labels.
Produces per-concept and overall metrics for both legacy and shadow systems.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ── Concept mapping: align legacy and shadow concept IDs ──────────────────
# Legacy uses pattern_ids, shadow uses technique_ids/strategy_ids
# This mapping defines which concepts overlap between systems.

CONCEPT_ALIASES = {
    # Concepts detectable by both systems
    "sliding_window_fixed": {
        "legacy": "sliding_window_fixed",
        "shadow": "fixed_window_maintenance",  # or "sliding_window" strategy
    },
    "sliding_window_variable": {
        "legacy": "sliding_window_variable",
        "shadow": "loop_state_tracking",  # or "sliding_window" strategy
    },
    "two_pointers_opposite": {
        "legacy": "two_pointers_opposite",
        "shadow": "bidirectional_index_scan",  # or "two_pointers_opposite" strategy
    },
    "binary_search_standard": {
        "legacy": "binary_search_standard",
        "shadow": "binary_search",  # strategy
    },
    "monotonic_stack": {
        "legacy": "monotonic_stack",
        "shadow": "monotonic_stack_maintenance",  # or "monotonic_stack_strategy"
    },
    "union_find": {
        "legacy": "union_find",
        "shadow": "union_find",  # strategy
    },
    "dfs_recursive": {
        "legacy": "dfs_recursive",
        "shadow": "recursive_branching",  # technique
    },
    "bfs_shortest_path": {
        "legacy": "bfs_shortest_path",
        "shadow": "bfs_shortest_path",  # strategy
    },
    "backtracking_permutation": {
        "legacy": "backtracking_permutation",
        "shadow": "dfs_backtracking",  # strategy
    },
    "backtracking_subset": {
        "legacy": "backtracking_subset",
        "shadow": "dfs_backtracking",  # strategy
    },
}


def normalize_concept(concept_id: str, system: str) -> str:
    """Normalize a concept ID to the canonical evaluation concept.
    
    Maps both legacy and shadow IDs to a common vocabulary.
    """
    # Direct match
    if concept_id in CONCEPT_ALIASES:
        return concept_id
    
    # Check if this is a shadow-specific ID
    for canonical, mapping in CONCEPT_ALIASES.items():
        if system == "shadow" and mapping.get("shadow") == concept_id:
            return canonical
        if system == "legacy" and mapping.get("legacy") == concept_id:
            return canonical
    
    # Shadow-only concepts (no legacy equivalent)
    shadow_only = [
        "sequential_accumulation", "carry_propagation", "recursive_branching",
        "loop_state_tracking", "iterative_table_filling", "linked_list_traversal",
        "fixed_window_maintenance", "monotonic_stack_maintenance",
        "dp_top_down", "dp_bottom_up",
    ]
    if concept_id in shadow_only:
        return f"shadow_only_{concept_id}"
    
    # Legacy-only concepts
    return concept_id


def extract_detected_concepts(results: list, system: str) -> Dict[str, Set[str]]:
    """Extract detected concepts per submission from raw results.
    
    Returns dict: submission_id -> set of normalized concept IDs.
    """
    detected = {}
    
    for result in results:
        sub_id = result["submission_id"]
        
        if system == "legacy":
            legacy = result.get("legacy", {})
            if not legacy.get("success"):
                detected[sub_id] = set()
                continue
            
            patterns = legacy.get("detected_patterns", [])
            concepts = set()
            for p in patterns:
                pid = p.get("pattern_id", "")
                conf = p.get("confidence", 0.0)
                evidence = p.get("evidence", [])
                # Output pipeline only includes detected patterns (filtered by coordinator)
                if conf > 0.0 or evidence:
                    concepts.add(normalize_concept(pid, "legacy"))
            detected[sub_id] = concepts
        
        elif system == "shadow":
            shadow = result.get("shadow", {})
            if not shadow.get("success"):
                detected[sub_id] = set()
                continue
            
            concepts = set()
            
            # From technique evidence
            for tech in shadow.get("technique_evidence", []):
                tid = tech.get("technique_id", "")
                concepts.add(normalize_concept(tid, "shadow"))
            
            # From strategy evidence
            for strat in shadow.get("strategy_evidence", []):
                sid = strat.get("strategy_id", "")
                concepts.add(normalize_concept(sid, "shadow"))
            
            # From match outcome primary strategy
            outcome = shadow.get("match_outcome", {})
            ps = outcome.get("primary_strategy")
            if ps:
                concepts.add(normalize_concept(ps, "shadow"))
            
            detected[sub_id] = concepts
    
    return detected


def load_ground_truth(ground_truth_path: str) -> Dict[str, dict]:
    """Load ground truth labels."""
    if not os.path.exists(ground_truth_path):
        return {}
    
    with open(ground_truth_path, 'r', encoding='utf-8') as f:
        labels = json.load(f)
    
    return {label["submission_id"]: label for label in labels}


def calculate_binary_metrics(
    tp: int, fp: int, fn: int, tn: int
) -> dict:
    """Calculate precision, recall, F1, FPR, FNR."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "support": tp + fn,
    }


def calculate_per_concept_metrics(
    detected: Dict[str, Set[str]],
    ground_truth: Dict[str, dict],
    system_name: str,
) -> dict:
    """Calculate per-concept metrics.
    
    For each concept:
    - A submission is a TRUE POSITIVE if the concept is in both detected and ground_truth.present
    - A submission is a FALSE POSITIVE if the concept is detected but NOT in ground_truth.present
    - A submission is a FALSE NEGATIVE if the concept is in ground_truth.present but NOT detected
    - A submission is a TRUE NEGATIVE if the concept is in neither
    
    Only submissions with ground truth labels are evaluated.
    """
    per_concept = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0})
    
    all_concepts = set()
    
    for sub_id, gt in ground_truth.items():
        detected_concepts = detected.get(sub_id, set())
        present = set(gt.get("present", []))
        absent = set(gt.get("absent", []))
        uncertain = set(gt.get("uncertain", []))
        
        # All concepts that appear in any ground truth
        all_concepts.update(present)
        all_concepts.update(absent)
        all_concepts.update(uncertain)
        
        for concept in all_concepts:
            in_detected = concept in detected_concepts
            in_present = concept in present
            in_absent = concept in absent
            in_uncertain = concept in uncertain
            
            if in_present:
                if in_detected:
                    per_concept[concept]["tp"] += 1
                else:
                    per_concept[concept]["fn"] += 1
            elif in_absent:
                if in_detected:
                    per_concept[concept]["fp"] += 1
                else:
                    per_concept[concept]["tn"] += 1
            # Skip uncertain cases for strict metrics
    
    # Calculate metrics per concept
    results = {}
    for concept in sorted(all_concept for all_concept in all_concepts):
        counts = per_concept[concept]
        metrics = calculate_binary_metrics(
            counts["tp"], counts["fp"], counts["fn"], counts["tn"]
        )
        metrics["concept"] = concept
        metrics["system"] = system_name
        results[concept] = metrics
    
    return results


def calculate_overall_metrics(per_concept: dict) -> dict:
    """Calculate micro and macro averages from per-concept metrics."""
    total_tp = sum(m["tp"] for m in per_concept.values())
    total_fp = sum(m["fp"] for m in per_concept.values())
    total_fn = sum(m["fn"] for m in per_concept.values())
    total_tn = sum(m["tn"] for m in per_concept.values())
    
    # Micro average
    micro = calculate_binary_metrics(total_tp, total_fp, total_fn, total_tn)
    micro["average_type"] = "micro"
    
    # Macro average (simple mean of per-concept metrics)
    valid_concepts = [m for m in per_concept.values() if m["support"] > 0]
    if valid_concepts:
        macro = {
            "precision": round(sum(m["precision"] for m in valid_concepts) / len(valid_concepts), 4),
            "recall": round(sum(m["recall"] for m in valid_concepts) / len(valid_concepts), 4),
            "f1": round(sum(m["f1"] for m in valid_concepts) / len(valid_concepts), 4),
            "false_positive_rate": round(sum(m["false_positive_rate"] for m in valid_concepts) / len(valid_concepts), 4),
            "false_negative_rate": round(sum(m["false_negative_rate"] for m in valid_concepts) / len(valid_concepts), 4),
            "average_type": "macro",
            "num_concepts": len(valid_concepts),
        }
    else:
        macro = {"average_type": "macro", "num_concepts": 0}
    
    # Weighted average (weighted by support)
    total_support = sum(m["support"] for m in valid_concepts)
    if total_support > 0:
        weighted = {
            "precision": round(sum(m["precision"] * m["support"] for m in valid_concepts) / total_support, 4),
            "recall": round(sum(m["recall"] * m["support"] for m in valid_concepts) / total_support, 4),
            "f1": round(sum(m["f1"] * m["support"] for m in valid_concepts) / total_support, 4),
            "false_positive_rate": round(sum(m["false_positive_rate"] * m["support"] for m in valid_concepts) / total_support, 4),
            "false_negative_rate": round(sum(m["false_negative_rate"] * m["support"] for m in valid_concepts) / total_support, 4),
            "average_type": "weighted",
            "total_support": total_support,
        }
    else:
        weighted = {"average_type": "weighted", "total_support": 0}
    
    return {
        "micro": micro,
        "macro": macro,
        "weighted": weighted,
    }


def evaluate_confidence_calibration(
    results: list,
    ground_truth: Dict[str, dict],
    system: str,
) -> dict:
    """Evaluate whether confidence scores correlate with correctness."""
    # Group confidence scores by whether the detection was correct
    correct_confs = []
    incorrect_confs = []
    
    for result in results:
        sub_id = result["submission_id"]
        gt = ground_truth.get(sub_id)
        if not gt:
            continue
        
        present = set(gt.get("present", []))
        
        if system == "legacy":
            legacy = result.get("legacy", {})
            if not legacy.get("success"):
                continue
            for pattern in legacy.get("detected_patterns", []):
                pid = pattern.get("pattern_id", "")
                conf = pattern.get("confidence", 0.0)
                if pattern.get("detected", False) and conf > 0.0:
                    if pid in present:
                        correct_confs.append(conf)
                    else:
                        incorrect_confs.append(conf)
        
        elif system == "shadow":
            shadow = result.get("shadow", {})
            if not shadow.get("success"):
                continue
            for tech in shadow.get("technique_evidence", []):
                tid = tech.get("technique_id", "")
                conf = tech.get("presence_confidence", 0.0)
                if conf > 0.0:
                    if tid in present:
                        correct_confs.append(conf)
                    else:
                        incorrect_confs.append(conf)
            for strat in shadow.get("strategy_evidence", []):
                sid = strat.get("strategy_id", "")
                conf = strat.get("confidence", 0.0)
                if conf > 0.0:
                    if sid in present:
                        correct_confs.append(conf)
                    else:
                        incorrect_confs.append(conf)
    
    # Calculate calibration metrics
    avg_correct = sum(correct_confs) / len(correct_confs) if correct_confs else 0
    avg_incorrect = sum(incorrect_confs) / len(incorrect_confs) if incorrect_confs else 0
    
    # Confidence distribution
    bins = [(0.0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.01)]
    distribution = {}
    for low, high in bins:
        bin_label = f"{low:.1f}-{high:.1f}"
        correct_in_bin = sum(1 for c in correct_confs if low <= c < high)
        incorrect_in_bin = sum(1 for c in incorrect_confs if low <= c < high)
        total_in_bin = correct_in_bin + incorrect_in_bin
        distribution[bin_label] = {
            "total": total_in_bin,
            "correct": correct_in_bin,
            "incorrect": incorrect_in_bin,
            "accuracy": correct_in_bin / total_in_bin if total_in_bin > 0 else None,
        }
    
    return {
        "system": system,
        "avg_confidence_correct": round(avg_correct, 4),
        "avg_confidence_incorrect": round(avg_incorrect, 4),
        "num_correct": len(correct_confs),
        "num_incorrect": len(incorrect_confs),
        "distribution_by_confidence_bin": distribution,
        "calibration_assessment": "appears_correlated" if avg_correct > avg_incorrect else "not_correlated",
    }


def calculate_comparison_table(
    legacy_per_concept: dict,
    shadow_per_concept: dict,
) -> list:
    """Create legacy vs shadow comparison table."""
    all_concepts = set(legacy_per_concept.keys()) | set(shadow_per_concept.keys())
    
    table = []
    for concept in sorted(all_concepts):
        legacy_m = legacy_per_concept.get(concept, {})
        shadow_m = shadow_per_concept.get(concept, {})
        
        table.append({
            "concept": concept,
            "legacy_precision": legacy_m.get("precision", None),
            "legacy_recall": legacy_m.get("recall", None),
            "legacy_f1": legacy_m.get("f1", None),
            "legacy_support": legacy_m.get("support", 0),
            "shadow_precision": shadow_m.get("precision", None),
            "shadow_recall": shadow_m.get("recall", None),
            "shadow_f1": shadow_m.get("f1", None),
            "shadow_support": shadow_m.get("support", 0),
            "precision_diff": (
                round(shadow_m.get("precision", 0) - legacy_m.get("precision", 0), 4)
                if legacy_m.get("precision") is not None and shadow_m.get("precision") is not None
                else None
            ),
            "recall_diff": (
                round(shadow_m.get("recall", 0) - legacy_m.get("recall", 0), 4)
                if legacy_m.get("recall") is not None and shadow_m.get("recall") is not None
                else None
            ),
            "f1_diff": (
                round(shadow_m.get("f1", 0) - legacy_m.get("f1", 0), 4)
                if legacy_m.get("f1") is not None and shadow_m.get("f1") is not None
                else None
            ),
        })
    
    return table


def run_full_evaluation(
    raw_results_path: str,
    ground_truth_path: str,
    output_dir: str,
) -> dict:
    """Run complete evaluation and save all metrics."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Load data
    with open(raw_results_path, 'r', encoding='utf-8') as f:
        raw_results = json.load(f)
    
    ground_truth = load_ground_truth(ground_truth_path) if ground_truth_path else {}
    
    if not ground_truth:
        print("WARNING: No ground truth labels found. Using target_concepts as proxy.")
        # Use target_concepts as proxy ground truth
        for result in raw_results:
            gt_entry = {
                "submission_id": result["submission_id"],
                "present": result.get("target_concepts", []),
                "absent": [],
                "uncertain": [],
                "reasoning": {},
            }
            ground_truth[result["submission_id"]] = gt_entry
    
    # Extract detected concepts
    legacy_detected = extract_detected_concepts(raw_results, "legacy")
    shadow_detected = extract_detected_concepts(raw_results, "shadow")
    
    print(f"\nEvaluation Summary:")
    print(f"  Total submissions: {len(raw_results)}")
    print(f"  With ground truth: {len(ground_truth)}")
    
    # Count detected concepts per system
    legacy_total = sum(len(v) for v in legacy_detected.values())
    shadow_total = sum(len(v) for v in shadow_detected.values())
    print(f"  Legacy total detections: {legacy_total}")
    print(f"  Shadow total detections: {shadow_total}")
    
    # Per-concept metrics
    legacy_per_concept = calculate_per_concept_metrics(legacy_detected, ground_truth, "legacy")
    shadow_per_concept = calculate_per_concept_metrics(shadow_detected, ground_truth, "shadow")
    
    # Overall metrics
    legacy_overall = calculate_overall_metrics(legacy_per_concept)
    shadow_overall = calculate_overall_metrics(shadow_per_concept)
    
    # Comparison table
    comparison = calculate_comparison_table(legacy_per_concept, shadow_per_concept)
    
    # Confidence calibration
    legacy_calibration = evaluate_confidence_calibration(raw_results, ground_truth, "legacy")
    shadow_calibration = evaluate_confidence_calibration(raw_results, ground_truth, "shadow")
    
    # Save results
    results = {
        "legacy_overall": legacy_overall,
        "shadow_overall": shadow_overall,
        "legacy_per_concept": legacy_per_concept,
        "shadow_per_concept": shadow_per_concept,
        "comparison": comparison,
        "legacy_confidence_calibration": legacy_calibration,
        "shadow_confidence_calibration": shadow_calibration,
    }
    
    # Save overall metrics
    with open(os.path.join(output_dir, "overall_metrics.json"), 'w') as f:
        json.dump({
            "legacy": legacy_overall,
            "shadow": shadow_overall,
        }, f, indent=2)
    
    # Save per-concept metrics as CSV
    csv_lines = ["concept,system,precision,recall,f1,false_positive_rate,false_negative_rate,tp,fp,fn,tn,support"]
    for concept, metrics in sorted(legacy_per_concept.items()):
        csv_lines.append(f"{concept},legacy,{metrics['precision']},{metrics['recall']},{metrics['f1']},{metrics['false_positive_rate']},{metrics['false_negative_rate']},{metrics['tp']},{metrics['fp']},{metrics['fn']},{metrics['tn']},{metrics['support']}")
    for concept, metrics in sorted(shadow_per_concept.items()):
        csv_lines.append(f"{concept},shadow,{metrics['precision']},{metrics['recall']},{metrics['f1']},{metrics['false_positive_rate']},{metrics['false_negative_rate']},{metrics['tp']},{metrics['fp']},{metrics['fn']},{metrics['tn']},{metrics['support']}")
    
    with open(os.path.join(output_dir, "per_concept_metrics.csv"), 'w') as f:
        f.write("\n".join(csv_lines))
    
    # Save comparison table
    comp_lines = ["concept,legacy_precision,legacy_recall,legacy_f1,legacy_support,shadow_precision,shadow_recall,shadow_f1,shadow_support,precision_diff,recall_diff,f1_diff"]
    for row in comparison:
        comp_lines.append(f"{row['concept']},{row.get('legacy_precision', '')},{row.get('legacy_recall', '')},{row.get('legacy_f1', '')},{row.get('legacy_support', 0)},{row.get('shadow_precision', '')},{row.get('shadow_recall', '')},{row.get('shadow_f1', '')},{row.get('shadow_support', 0)},{row.get('precision_diff', '')},{row.get('recall_diff', '')},{row.get('f1_diff', '')}")
    
    with open(os.path.join(output_dir, "legacy_vs_shadow.csv"), 'w') as f:
        f.write("\n".join(comp_lines))
    
    # Save calibration
    with open(os.path.join(output_dir, "confidence_calibration.json"), 'w') as f:
        json.dump({
            "legacy": legacy_calibration,
            "shadow": shadow_calibration,
        }, f, indent=2)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"LEGACY SYSTEM:")
    if "micro" in legacy_overall:
        print(f"  Micro: P={legacy_overall['micro']['precision']:.3f} R={legacy_overall['micro']['recall']:.3f} F1={legacy_overall['micro']['f1']:.3f}")
    if "macro" in legacy_overall:
        print(f"  Macro: P={legacy_overall['macro']['precision']:.3f} R={legacy_overall['macro']['recall']:.3f} F1={legacy_overall['macro']['f1']:.3f}")
    
    print(f"\nSHADOW SYSTEM:")
    if "micro" in shadow_overall:
        print(f"  Micro: P={shadow_overall['micro']['precision']:.3f} R={shadow_overall['micro']['recall']:.3f} F1={shadow_overall['micro']['f1']:.3f}")
    if "macro" in shadow_overall:
        print(f"  Macro: P={shadow_overall['macro']['precision']:.3f} R={shadow_overall['macro']['recall']:.3f} F1={shadow_overall['macro']['f1']:.3f}")
    
    print(f"\nResults saved to: {output_dir}")
    
    return results


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    raw_results = str(base_dir / "results" / "raw_outputs" / "raw_results.json")
    ground_truth = str(base_dir / "ground_truth" / "labels.json")
    output_dir = str(base_dir / "results" / "metrics")
    
    if not os.path.exists(raw_results):
        print("Raw results not found. Please run run_evaluation.py first.")
        sys.exit(1)
    
    run_full_evaluation(raw_results, ground_truth, output_dir)
