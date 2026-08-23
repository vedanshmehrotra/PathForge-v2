"""Run large corpus evaluation: production AST vs shadow architecture."""
import json
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, ".")

from pathforge.ast_analysis.shadow.tests.large_corpus import get_corpus
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
from pathforge.api.services.analysis import run_analysis


def run_production(code):
    try:
        result = run_analysis(code, "python")
        ast_r = result.get("ast", {})
        detected = [p.get("pattern_id", p.get("name", "")) for p in ast_r.get("detected_patterns", []) if p.get("detected", True)]
        match = result.get("match_result", {})
        return {"detected": detected, "count": len(detected), "match": match.get("match", "NO_MATCH")}
    except:
        return {"detected": [], "count": 0, "match": "ERROR"}


def build_groups(expected_strategy):
    if not expected_strategy:
        return []
    return [{"id": "group_0", "required": [expected_strategy], "optional": [], "excluded": [], "threshold": 0.5, "authority_tier": "llm_proposed", "patterns": []}]


def main():
    corpus = get_corpus()
    total = len(corpus)
    t0 = time.time()

    # Counters
    with_strategy = 0
    without_strategy = 0
    tp = fp = fn = tn = 0
    spurious = 0
    correct_unres = 0
    errors = 0
    strat_data = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "total": 0})

    # Distribution
    no_tech = no_strat = strat_no_match = one_match = multi_match = 0

    # Failure taxonomy
    failure_taxonomy = Counter()

    results = []

    for i, case in enumerate(corpus):
        name = case["name"]
        code = case["code"]
        expected = case["expected_strategy"]
        category = case["category"]

        prod = run_production(code)
        groups = build_groups(expected)

        try:
            shadow = run_shadow_analysis(code, solution_groups=groups if groups else None)
        except:
            shadow = None

        if shadow is None or shadow.get("error"):
            errors += 1
            results.append({"name": name, "category": category, "expected": expected,
                          "classification": "shadow_error"})
            continue

        outcome = shadow.get("match_outcome", {}).get("outcome", "UNKNOWN")
        strategies = [s["strategy_id"] for s in shadow.get("strategy_evidence", [])]
        techniques = [t["technique_id"] for t in shadow.get("technique_evidence", [])]
        sat = shadow.get("match_outcome", {}).get("satisfaction", 0.0)
        satisfied = shadow.get("match_outcome", {}).get("satisfied_group_ids", [])

        # Distribution
        if not techniques: no_tech += 1
        elif not strategies: no_strat += 1
        elif not satisfied: strat_no_match += 1
        elif len(satisfied) == 1: one_match += 1
        else: multi_match += 1

        # Classification
        if expected:
            with_strategy += 1
            strat_data[expected]["total"] += 1
            if expected in strategies and outcome == "CONFIRMED":
                tp += 1
                strat_data[expected]["tp"] += 1
                classification = "true_positive"
            elif outcome == "CONFIRMED" and expected not in strategies:
                fp += 1
                strat_data[expected]["fp"] += 1
                classification = "false_positive"
            elif expected in strategies and outcome != "CONFIRMED":
                fn += 1
                strat_data[expected]["fn"] += 1
                classification = "false_negative"
            else:
                fn += 1
                strat_data[expected]["fn"] += 1
                classification = "false_negative"
                # Categorize failure
                if not techniques:
                    failure_taxonomy["no_techniques_extracted"] += 1
                elif not strategies:
                    failure_taxonomy["technique_but_no_strategy"] += 1
                else:
                    failure_taxonomy["strategy_not_satisfied"] += 1
        else:
            without_strategy += 1
            if outcome == "CONFIRMED":
                spurious += 1
                classification = "spurious_confirmed"
            else:
                correct_unres += 1
                classification = "correct_unresolved"

        results.append({
            "name": name,
            "category": category,
            "expected": expected,
            "prod_patterns": prod["detected"],
            "prod_match": prod["match"],
            "shadow_outcome": outcome,
            "shadow_satisfaction": sat,
            "shadow_strategies": strategies,
            "shadow_techniques": techniques,
            "classification": classification,
        })

    elapsed = time.time() - t0

    # Build output
    output = {
        "corpus_size": total,
        "elapsed_seconds": round(elapsed, 1),
        "errors": errors,
        "summary": {
            "with_strategy": with_strategy,
            "without_strategy": without_strategy,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "spurious": spurious,
            "correct_unresolved": correct_unres,
            "precision": tp / max(1, tp + fp),
            "recall": tp / max(1, tp + fn),
            "f1": 2 * tp / max(1, 2 * tp + fp + fn),
            "false_confirmed_rate": spurious / max(1, without_strategy),
            "correct_unresolved_rate": correct_unres / max(1, without_strategy),
        },
        "distribution": {
            "no_techniques": no_tech,
            "techniques_no_strategy": no_strat,
            "strategy_no_match": strat_no_match,
            "one_satisfied_group": one_match,
            "multiple_satisfied_groups": multi_match,
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
            for s, d in sorted(strat_data.items())
        },
        "failure_taxonomy": dict(failure_taxonomy.most_common()),
        "cases": results,
    }

    with open("large_corpus_results.json", "w") as f:
        json.dump(output, f, indent=2)

    # Print
    s = output["summary"]
    d = output["distribution"]
    print(f"\n{'='*65}")
    print(f"  LARGE CORPUS VALIDATION ({total} cases, {elapsed:.1f}s)")
    print(f"{'='*65}")
    print(f"  Errors: {errors}")
    print(f"\n  --- SAFETY ---")
    print(f"  Spurious CONFIRMED:    {spurious} ({output['summary']['false_confirmed_rate']:.1%})")
    print(f"  Correct UNRESOLVED:    {correct_unres} ({output['summary']['correct_unresolved_rate']:.1%})")
    print(f"\n  --- ACCURACY (cases with expected strategy: {with_strategy}) ---")
    print(f"  True positive:         {tp} ({tp/max(1,with_strategy):.1%})")
    print(f"  False positive:        {fp}")
    print(f"  False negative:        {fn}")
    print(f"  Precision:             {s['precision']:.3f}")
    print(f"  Recall:                {s['recall']:.3f}")
    print(f"  F1:                    {s['f1']:.3f}")
    print(f"\n  --- DISTRIBUTION ---")
    print(f"  No techniques:         {d['no_techniques']}")
    print(f"  Techniques, no strat:  {d['techniques_no_strategy']}")
    print(f"  Strategy, no match:    {d['strategy_no_match']}")
    print(f"  One satisfied group:   {d['one_satisfied_group']}")
    print(f"  Multiple satisfied:    {d['multiple_satisfied_groups']}")
    print(f"\n  --- PER STRATEGY ---")
    for strat, data in output["per_strategy"].items():
        print(f"    {strat:30s} P={data['precision']:.2f} R={data['recall']:.2f} F1={data['f1']:.2f} "
              f"(TP={data['tp']} FP={data['fp']} FN={data['fn']})")
    print(f"\n  --- FAILURE TAXONOMY ---")
    for cause, count in output["failure_taxonomy"].items():
        print(f"    {cause}: {count}")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()
