"""Evaluation runner for Phase 5C.

Runs the disjoint evaluation corpus through the shadow analysis system
and collects metrics for per-strategy analysis.
"""
import json
import sys
import time
from collections import defaultdict

from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
from pathforge.ast_analysis.shadow.tests.evaluation_corpus import CORPUS


def run_evaluation():
    """Run the full evaluation corpus and collect results."""
    results = []
    strategy_metrics = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0})
    technique_metrics = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0})

    total = len(CORPUS)
    print(f"Running evaluation on {total} cases...")

    for i, case in enumerate(CORPUS):
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i + 1}/{total}")

        name = case["name"]
        code = case["code"]
        expected_strategy = case["expected_strategy"]
        expected_techniques = case.get("expected_techniques", [])

        try:
            start = time.time()
            result = run_shadow_analysis(code)
            latency_ms = (time.time() - start) * 1000

            if result is None:
                detected_strategies = set()
                detected_techniques = set()
            else:
                detected_strategies = {s["strategy_id"] for s in result["strategy_evidence"]}
                detected_techniques = {t["technique_id"] for t in result["technique_evidence"]}

            # Strategy-level metrics
            if expected_strategy:
                if expected_strategy in detected_strategies:
                    strategy_metrics[expected_strategy]["tp"] += 1
                else:
                    strategy_metrics[expected_strategy]["fn"] += 1
                # Check for false positives (detected but not expected)
                for ds in detected_strategies:
                    if ds != expected_strategy:
                        strategy_metrics[ds]["fp"] += 1
            else:
                # No expected strategy — any detection is a false positive
                for ds in detected_strategies:
                    strategy_metrics[ds]["fp"] += 1

            # Technique-level metrics
            for expected_t in expected_techniques:
                if expected_t in detected_techniques:
                    technique_metrics[expected_t]["tp"] += 1
                else:
                    technique_metrics[expected_t]["fn"] += 1
            for dt in detected_techniques:
                if dt not in expected_techniques:
                    technique_metrics[dt]["fp"] += 1

            # Safety outcome
            if expected_strategy:
                if expected_strategy in detected_strategies:
                    safety = "correct_confirmed"
                elif len(detected_strategies) == 0:
                    safety = "incorrect_unresolved"
                else:
                    safety = "incorrect_unresolved"
            else:
                if len(detected_strategies) == 0:
                    safety = "correct_unresolved"
                else:
                    safety = "false_positive"

            results.append({
                "name": name,
                "expected_strategy": expected_strategy,
                "detected_strategies": sorted(detected_strategies),
                "detected_techniques": sorted(detected_techniques),
                "safety": safety,
                "latency_ms": round(latency_ms, 2),
            })

        except Exception as e:
            results.append({
                "name": name,
                "expected_strategy": expected_strategy,
                "detected_strategies": [],
                "detected_techniques": [],
                "safety": "error",
                "error": str(e),
                "latency_ms": 0,
            })

    return results, strategy_metrics, technique_metrics


def compute_metrics(strategy_metrics, technique_metrics):
    """Compute precision, recall, F1 for each strategy and technique."""
    metrics = {}

    for strat_id, counts in sorted(strategy_metrics.items()):
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        metrics[f"strategy_{strat_id}"] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
        }

    for tech_id, counts in sorted(technique_metrics.items()):
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        metrics[f"technique_{tech_id}"] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
        }

    return metrics


def analyze_results(results, metrics):
    """Analyze and print key metrics."""
    total = len(results)

    # Safety outcomes
    safety_counts = defaultdict(int)
    for r in results:
        safety_counts[r["safety"]] += 1

    print("\n" + "=" * 60)
    print("SAFETY OUTCOMES")
    print("=" * 60)
    for safety, count in sorted(safety_counts.items()):
        print(f"  {safety}: {count} ({count/total*100:.1f}%)")

    # Overall metrics
    total_tp = sum(m["tp"] for m in metrics.values() if m["tp"] > 0)
    total_fp = sum(m["fp"] for m in metrics.values() if m["fp"] > 0)
    total_fn = sum(m["fn"] for m in metrics.values() if m["fn"] > 0)

    print("\n" + "=" * 60)
    print("OVERALL METRICS")
    print("=" * 60)
    print(f"  Total true positives: {total_tp}")
    print(f"  Total false positives: {total_fp}")
    print(f"  Total false negatives: {total_fn}")

    # Per-strategy metrics
    print("\n" + "=" * 60)
    print("PER-STRATEGY METRICS")
    print("=" * 60)
    for key in sorted(metrics.keys()):
        if key.startswith("strategy_"):
            m = metrics[key]
            strat_name = key.replace("strategy_", "")
            print(f"  {strat_name}: P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} (TP={m['tp']} FP={m['fp']} FN={m['fn']})")

    # Per-technique metrics
    print("\n" + "=" * 60)
    print("PER-TECHNIQUE METRICS")
    print("=" * 60)
    for key in sorted(metrics.keys()):
        if key.startswith("technique_"):
            m = metrics[key]
            tech_name = key.replace("technique_", "")
            print(f"  {tech_name}: P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} (TP={m['tp']} FP={m['fp']} FN={m['fn']})")

    # False positives analysis
    print("\n" + "=" * 60)
    print("FALSE POSITIVES")
    print("=" * 60)
    fps = [r for r in results if r["safety"] == "false_positive"]
    for fp in fps:
        print(f"  {fp['name']}: expected=None, detected={fp['detected_strategies']}")

    # Latency
    latencies = [r["latency_ms"] for r in results if r["latency_ms"] > 0]
    if latencies:
        print("\n" + "=" * 60)
        print("LATENCY")
        print("=" * 60)
        print(f"  Mean: {sum(latencies)/len(latencies):.2f}ms")
        print(f"  Min: {min(latencies):.2f}ms")
        print(f"  Max: {max(latencies):.2f}ms")

    return {
        "total": total,
        "safety_counts": dict(safety_counts),
        "total_tp": total_tp,
        "total_fp": total_fp,
        "total_fn": total_fn,
    }


if __name__ == "__main__":
    results, strategy_metrics, technique_metrics = run_evaluation()
    metrics = compute_metrics(strategy_metrics, technique_metrics)
    summary = analyze_results(results, metrics)

    # Save full results
    output = {
        "summary": summary,
        "metrics": metrics,
        "results": results,
    }
    with open("phase5c_evaluation_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nFull results saved to phase5c_evaluation_results.json")
