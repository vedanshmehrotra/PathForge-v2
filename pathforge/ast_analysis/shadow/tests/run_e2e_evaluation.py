"""End-to-end architecture evaluation.

Runs both production AST detection and the new shadow architecture
on every case in the evaluation corpus, then compares results.

Key comparison:
- Production: AST pattern detection + flat pattern matching
- Shadow: structural facts → techniques → strategies → solution-group matching

For cases WITH expected strategy: builds solution groups and tests shadow matching.
For cases WITHOUT expected strategy: tests whether shadow produces spurious CONFIRMED.
"""
import ast
import json
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, ".")

from pathforge.ast_analysis.shadow.tests.evaluation_corpus import CORPUS
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
from pathforge.api.services.analysis import run_analysis


def run_production_ast(code: str) -> dict:
    """Run the production AST detector on code."""
    try:
        result = run_analysis(code, "python")
        ast_result = result.get("ast", {})
        detected = [
            p.get("pattern_id", p.get("name", ""))
            for p in ast_result.get("detected_patterns", [])
            if p.get("detected", True)
        ]
        match = result.get("match_result", {})
        return {
            "detected_patterns": detected,
            "pattern_count": len(detected),
            "match_result": match.get("match", "NO_MATCH"),
        }
    except Exception as e:
        return {"detected_patterns": [], "pattern_count": 0, "match_result": "ERROR", "error": str(e)}


def run_shadow_full(code: str, solution_groups=None) -> dict:
    """Run the full shadow pipeline."""
    try:
        result = run_shadow_analysis(code, solution_groups=solution_groups)
        if result is None:
            return {"error": "shadow_runner returned None"}
        return result
    except Exception as e:
        return {"error": str(e)}


def build_solution_groups(expected_strategy, expected_techniques):
    """Build solution groups from expected strategy/techniques for shadow matching.

    Only builds groups when we have a positive expected strategy.
    """
    if not expected_strategy:
        return []

    required = [expected_strategy]
    optional = list(expected_techniques or [])
    # Remove duplicates
    optional = [t for t in optional if t not in required]

    return [{
        "id": "group_0",
        "required": required,
        "optional": optional,
        "excluded": [],
        "threshold": 0.5,
        "authority_tier": "llm_proposed",
        "patterns": [],
    }]


def main():
    results = []

    # Counters
    total = 0
    cases_with_strategy = 0
    cases_without_strategy = 0

    # For cases WITH expected strategy
    true_positives = 0   # expected strategy detected AND confirmed
    false_negatives = 0  # expected strategy NOT detected
    false_positives_strategy = 0  # wrong strategy confirmed

    # For cases WITHOUT expected strategy
    correct_unresolved = 0  # no strategy expected, none confirmed
    spurious_confirmed = 0  # no strategy expected, but something confirmed

    # For ALL cases
    shadow_errors = 0
    prod_vs_shadow_disagree = 0

    # Metrics
    techniques_per_sub = []
    satisfaction_scores = []
    no_strategy_count = 0
    technique_only_count = 0

    strat_metrics = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "total": 0})

    for i, case in enumerate(CORPUS):
        name = case["name"]
        code = case["code"]
        expected_strategy = case.get("expected_strategy")
        expected_techniques = case.get("expected_techniques", [])

        total += 1

        # Run production AST
        prod = run_production_ast(code)

        # Build groups only when we have an expected strategy
        groups = build_solution_groups(expected_strategy, expected_techniques)

        # Run shadow
        shadow = run_shadow_full(code, solution_groups=groups if groups else None)

        # Extract shadow results
        shadow_outcome = {}
        shadow_strategies = []
        shadow_techniques = []
        shadow_facts = []
        satisfaction = 0.0
        outcome = "ERROR"

        if isinstance(shadow, dict) and not shadow.get("error"):
            shadow_outcome = shadow.get("match_outcome", {})
            shadow_strategies = [s["strategy_id"] for s in shadow.get("strategy_evidence", [])]
            shadow_techniques = [t["technique_id"] for t in shadow.get("technique_evidence", [])]
            shadow_facts = list(set(f["fact_type"] for f in shadow.get("structural_facts", [])))
            satisfaction = shadow_outcome.get("satisfaction", 0.0)
            outcome = shadow_outcome.get("outcome", "UNKNOWN")
        elif isinstance(shadow, dict) and shadow.get("error"):
            shadow_errors += 1

        # Classify
        if expected_strategy:
            cases_with_strategy += 1
            strat_metrics[expected_strategy]["total"] += 1

            if expected_strategy in shadow_strategies and outcome == "CONFIRMED":
                true_positives += 1
                strat_metrics[expected_strategy]["tp"] += 1
                classification = "true_positive"
            elif expected_strategy in shadow_strategies and outcome != "CONFIRMED":
                false_negatives += 1
                strat_metrics[expected_strategy]["fn"] += 1
                classification = "false_negative_detected_not_confirmed"
            elif expected_strategy not in shadow_strategies and outcome == "CONFIRMED":
                # Wrong strategy confirmed
                false_positives_strategy += 1
                strat_metrics[expected_strategy]["fp"] += 1
                classification = "false_positive_wrong_strategy"
            else:
                false_negatives += 1
                strat_metrics[expected_strategy]["fn"] += 1
                classification = "false_negative_not_detected"
        else:
            cases_without_strategy += 1
            if outcome == "CONFIRMED":
                spurious_confirmed += 1
                classification = "spurious_confirmed"
            else:
                correct_unresolved += 1
                classification = "correct_unresolved"

        # Track metrics
        techniques_per_sub.append(len(shadow_techniques))
        satisfaction_scores.append(satisfaction)
        if not shadow_strategies:
            no_strategy_count += 1
        if shadow_techniques and not shadow_strategies:
            technique_only_count += 1

        prod_has_patterns = prod["pattern_count"] > 0
        shadow_confirmed = outcome == "CONFIRMED"
        if prod_has_patterns != shadow_confirmed:
            prod_vs_shadow_disagree += 1

        results.append({
            "name": name,
            "expected_strategy": expected_strategy,
            "expected_techniques": expected_techniques,
            "prod_patterns": prod["detected_patterns"],
            "prod_match": prod["match_result"],
            "shadow_outcome": outcome,
            "shadow_satisfaction": satisfaction,
            "shadow_strategies": shadow_strategies,
            "shadow_techniques": shadow_techniques,
            "shadow_fact_types": shadow_facts,
            "classification": classification,
        })

    # Save JSON
    output = {
        "summary": {
            "total": total,
            "cases_with_strategy": cases_with_strategy,
            "cases_without_strategy": cases_without_strategy,
            "true_positives": true_positives,
            "false_negatives": false_negatives,
            "false_positives_strategy": false_positives_strategy,
            "correct_unresolved": correct_unresolved,
            "spurious_confirmed": spurious_confirmed,
            "shadow_errors": shadow_errors,
            "prod_vs_shadow_disagree": prod_vs_shadow_disagree,
            "true_positive_rate": true_positives / max(1, cases_with_strategy),
            "false_negative_rate": false_negatives / max(1, cases_with_strategy),
            "false_positive_rate_strategy": false_positives_strategy / max(1, cases_with_strategy),
            "spurious_confirmed_rate": spurious_confirmed / max(1, cases_without_strategy),
            "correct_unresolved_rate": correct_unresolved / max(1, cases_without_strategy),
            "avg_techniques_per_submission": sum(techniques_per_sub) / max(1, len(techniques_per_sub)),
            "pct_no_strategy": no_strategy_count / max(1, total),
            "pct_technique_only": technique_only_count / max(1, total),
            "satisfaction_mean": sum(satisfaction_scores) / max(1, len(satisfaction_scores)),
        },
        "per_strategy": {
            s: {
                "total": d["total"],
                "tp": d["tp"],
                "fp": d["fp"],
                "fn": d["fn"],
                "precision": d["tp"] / max(1, d["tp"] + d["fp"]),
                "recall": d["tp"] / max(1, d["tp"] + d["fn"]),
                "f1": 2 * d["tp"] / max(1, 2 * d["tp"] + d["fp"] + d["fn"]),
            }
            for s, d in sorted(strat_metrics.items())
        },
        "cases": results,
    }

    with open("e2e_architecture_evaluation.json", "w") as f:
        json.dump(output, f, indent=2)

    # Print summary
    s = output["summary"]
    print(f"\n{'='*65}")
    print(f"  END-TO-END ARCHITECTURE EVALUATION")
    print(f"{'='*65}")
    print(f"  Total cases:                  {s['total']}")
    print(f"  Cases WITH expected strategy: {s['cases_with_strategy']}")
    print(f"  Cases WITHOUT strategy:       {s['cases_without_strategy']}")
    print(f"  Shadow errors:                {s['shadow_errors']}")
    print()
    print(f"  --- Cases WITH expected strategy ---")
    print(f"  True positive (correctly confirmed):   {s['true_positives']:3d} ({s['true_positive_rate']:.1%})")
    print(f"  False negative (missed):               {s['false_negatives']:3d} ({s['false_negative_rate']:.1%})")
    print(f"  False positive (wrong strategy):       {s['false_positives_strategy']:3d} ({s['false_positive_rate_strategy']:.1%})")
    print()
    print(f"  --- Cases WITHOUT expected strategy ---")
    print(f"  Correctly unresolved:                  {s['correct_unresolved']:3d} ({s['correct_unresolved_rate']:.1%})")
    print(f"  Spurious confirmed:                    {s['spurious_confirmed']:3d} ({s['spurious_confirmed_rate']:.1%})")
    print()
    print(f"  --- Overall ---")
    print(f"  Avg techniques/submission:   {s['avg_techniques_per_submission']:.1f}")
    print(f"  % with no strategy evidence: {s['pct_no_strategy']:.1%}")
    print(f"  % technique-only matching:   {s['pct_no_technique_only' if 'pct_no_technique_only' in s else 'pct_technique_only']:.1%}")
    print(f"  Prod vs shadow disagree:     {s['prod_vs_shadow_disagree']}")
    print()
    print(f"  PER-STRATEGY METRICS:")
    for strat, data in output["per_strategy"].items():
        print(f"    {strat:30s} P={data['precision']:.2f} R={data['recall']:.2f} F1={data['f1']:.2f} "
              f"(TP={data['tp']} FP={data['fp']} FN={data['fn']})")

    # False positives
    fps = [r for r in results if r["classification"] == "false_positive_wrong_strategy"]
    if fps:
        print(f"\n  FALSE POSITIVES (wrong strategy confirmed):")
        for r in fps:
            print(f"    {r['name']}: expected={r['expected_strategy']}, got={r['shadow_strategies']}")

    # Spurious
    sp = [r for r in results if r["classification"] == "spurious_confirmed"]
    if sp:
        print(f"\n  SPURIOUS CONFIRMATIONS (no expected strategy, but confirmed):")
        for r in sp:
            print(f"    {r['name']}: strategies={r['shadow_strategies']}, techniques={r['shadow_techniques']}")

    print(f"\n{'='*65}")


if __name__ == "__main__":
    main()
