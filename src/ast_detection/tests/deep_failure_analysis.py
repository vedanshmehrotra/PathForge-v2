"""Deep failure analysis: re-runs adversarial evaluation with full per-case tracking.

Outputs:
- Per-case results with seed dependency graph
- Precise classification: seed failure / inherited / true naming / true expression / true loop / true structural
- Corrected percentages
"""

import ast
import re
import sys
import json
from collections import defaultdict
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, field

sys.path.insert(0, '.')

from src.ast_detection.detector_interface import DetectionResult
from src.ast_detection.registry import get_all_detectors

# ============================================================================
# VARIANT GENERATORS (copied from adversarial_evaluation.py to ensure identical generation)
# ============================================================================

RENAME_MAPS = {
    "left_right": {
        "left": ["lo", "start", "l", "i", "low", "begin", "head_ptr"],
        "right": ["hi", "end", "r", "j", "high", "tail", "tail_ptr"],
    },
    "slow_fast": {
        "slow": ["sp", "first", "tortoise", "a"],
        "fast": ["fp", "second", "hare", "b"],
    },
    "dp_names": {
        "dp": ["table", "memo", "state", "cache", "f", "arr", "res"],
        "n": ["length", "size", "count", "num", "nums_len"],
    },
    "pointer_names": {
        "i": ["idx", "index", "pos", "p", "cursor"],
        "j": ["idx2", "index2", "pos2", "q", "cursor2"],
    },
    "general": {
        "result": ["res", "output", "ans", "answer", "ret"],
        "count": ["cnt", "num", "total", "sum"],
        "seen": ["visited", "checked", "found", "exists"],
    },
}


def rename_variables(code, rename_map):
    result = code
    for old_name, new_name in rename_map.items():
        result = re.sub(r'\b' + re.escape(old_name) + r'\b', new_name, result)
    return result


def generate_naming_variants(code):
    variants = []
    for map_name, name_map in RENAME_MAPS.items():
        for old_name, new_names in name_map.items():
            for new_name in new_names[:2]:
                if old_name in code:
                    renamed = rename_variables(code, {old_name: new_name})
                    if renamed != code:
                        variants.append((f"naming_{map_name}_{old_name}_{new_name}", renamed))
    return variants


def generate_loop_form_variants(code):
    variants = []
    range_pattern = re.compile(
        r'for (\w+) in range\(([^)]+)\):\s*\n((?:    .+\n?)+)', re.MULTILINE
    )
    for match in range_pattern.finditer(code):
        var_name = match.group(1)
        range_arg = match.group(2)
        body = match.group(3)
        if ',' not in range_arg:
            while_version = f"{var_name} = 0\nwhile {var_name} < {range_arg}:\n{body}    {var_name} += 1\n"
            variants.append(("loop_while_simple", while_version))

    for_pattern = re.compile(
        r'for (\w+) in (\w+):\s*\n((?:    .+\n?)+)', re.MULTILINE
    )
    for match in for_pattern.finditer(code):
        var_name = match.group(1)
        collection = match.group(2)
        body = match.group(3)
        new_var = f"_idx_{var_name}"
        body_renamed = body.replace(var_name, f"{collection}[{new_var}]")
        while_version = f"{new_var} = 0\nwhile {new_var} < len({collection}):\n{body_renamed}    {new_var} += 1\n"
        variants.append(("loop_while_collection", while_version))
    return variants


def generate_expression_variants(code):
    variants = []
    midpoint_patterns = [
        (r'\(left \+ right\) // 2', 'left + (right - left) // 2'),
        (r'\(lo \+ hi\) // 2', 'lo + (hi - lo) // 2'),
        (r'\(low \+ high\) // 2', 'low + (high - low) // 2'),
        (r'\(l \+ r\) // 2', 'l + (r - l) // 2'),
    ]
    for pattern, replacement in midpoint_patterns:
        if re.search(pattern, code):
            variants.append(("expr_midpoint", re.sub(pattern, replacement, code)))

    comparison_variants = [
        (r'(\w+) < (\w+)', r'not (\1 >= \2)'),
        (r'(\w+) > (\w+)', r'not (\1 <= \2)'),
    ]
    for pattern, replacement in comparison_variants[:1]:
        matches = list(re.finditer(pattern, code))
        if matches and len(matches) <= 3:
            m = matches[0]
            variant = code[:m.start()] + re.sub(pattern, replacement, code[m.start():m.end()]) + code[m.end():]
            if variant != code:
                variants.append(("expr_negated_comparison", variant))
    return variants


def generate_class_based_variant(code):
    variants = []
    func_pattern = re.compile(r'^(def (\w+)\([^)]*\):\s*\n(?:    .+\n?)+)', re.MULTILINE)
    for match in func_pattern.finditer(code):
        func_name = match.group(2)
        body_match = re.search(r':\s*\n((?:    .+\n?)+)', match.group(0))
        if not body_match:
            continue
        body = body_match.group(1)
        params_match = re.search(r'def \w+\(([^)]*)\)', match.group(0))
        params = params_match.group(1) if params_match else ''
        if 'class ' not in code:
            class_code = f"class Solution:\n    def {func_name}(self, {params}):\n{body}"
            variants.append((f"class_{func_name}", class_code))
    return variants


def generate_comprehensive_variants(code):
    all_variants = []
    for name, variant_code in generate_naming_variants(code):
        all_variants.append((name, variant_code))
    for name, variant_code in generate_loop_form_variants(code):
        all_variants.append((name, variant_code))
    for name, variant_code in generate_expression_variants(code):
        all_variants.append((name, variant_code))
    for name, variant_code in generate_class_based_variant(code):
        all_variants.append((name, variant_code))
    return all_variants


# ============================================================================
# EVALUATION
# ============================================================================

def run_detector(detector, code):
    try:
        tree = ast.parse(code)
        return detector.detect(tree)
    except (SyntaxError, ValueError):
        return DetectionResult(
            pattern_id=detector.pattern_id, confidence=0.0,
            evidence=[], detected=False
        )


def main():
    print("=" * 70)
    print("DEEP FAILURE ANALYSIS -- Seed vs Inherited vs True Variant")
    print("=" * 70)

    detectors = {d.pattern_id: d for d in get_all_detectors()}

    # Import seed corpus
    from src.ast_detection.tests.validate_all_36_detectors import VALIDATION_CORPUS

    # Phase 1: Run all seeds, record pass/fail
    print("\n[Phase 1] Running all seed cases...")
    seed_results = {}  # case_name -> {detected, pattern_id, code}
    for pattern_id, (positives, negatives) in VALIDATION_CORPUS.items():
        for name, code in positives:
            det = detectors.get(pattern_id)
            if not det:
                continue
            result = run_detector(det, code)
            detected = result.confidence > 0.0 and result.detected
            seed_results[name] = {
                "code": code,
                "pattern": pattern_id,
                "detected": detected,
                "is_positive": True,
            }
        for name, code in negatives:
            det = detectors.get(pattern_id)
            if not det:
                continue
            result = run_detector(det, code)
            detected = result.confidence > 0.0 and result.detected
            seed_results[name] = {
                "code": code,
                "pattern": pattern_id,
                "detected": detected,
                "is_positive": False,
            }

    total_seeds = len(seed_results)
    positive_seeds = [v for v in seed_results.values() if v["is_positive"]]
    seeds_passing = sum(1 for v in positive_seeds if v["detected"])
    seeds_failing = sum(1 for v in positive_seeds if not v["detected"])
    print(f"  Total seeds: {total_seeds}")
    print(f"  Positive seeds: {len(positive_seeds)}")
    print(f"  Seeds passing: {seeds_passing}")
    print(f"  Seeds failing: {seeds_failing}")

    # Phase 2: Generate variants from POSITIVE seeds only, track seed dependency
    print("\n[Phase 2] Generating variants from positive seeds...")
    all_cases = []
    # Store seed code -> seed name mapping
    seed_code_to_name = {}
    for v in positive_seeds:
        seed_code_to_name[v["code"]] = None  # will fill from name
    
    # Need to re-iterate to get names
    for name, v in seed_results.items():
        if v["is_positive"]:
            seed_code_to_name[v["code"]] = name
    
    variant_count = 0
    for case_name, v in seed_results.items():
        if not v["is_positive"]:
            continue
        if not v["detected"]:
            # Seed itself fails -- still generate variants to track inheritance
            pass
        
        variants = generate_comprehensive_variants(v["code"])
        for var_name, var_code in variants:
            try:
                ast.parse(var_code)
            except SyntaxError:
                continue
            variant_count += 1
            all_cases.append({
                "name": f"{case_name}_{var_name}",
                "code": var_code,
                "pattern": v["pattern"],
                "expected": True,
                "is_seed": False,
                "seed_name": case_name,
                "seed_detected": v["detected"],
                "variant_type": var_name.split("_")[0] if "_" in var_name else var_name,
            })

    print(f"  Generated {variant_count} variants")
    print(f"  Total cases (seeds + variants): {total_seeds + variant_count}")

    # Phase 3: Run all variants through their respective detectors
    print("\n[Phase 3] Running variants through detectors...")
    
    # Build results
    case_results = []
    for case in all_cases:
        det = detectors.get(case["pattern"])
        if not det:
            case_results.append({**case, "detected": False, "correct": True,
                                  "classification": "taxonomy_orphan"})
            continue
        result = run_detector(det, case["code"])
        detected = result.confidence > 0.0 and result.detected
        case_results.append({
            **case,
            "detected": detected,
            "confidence": result.confidence,
            "correct": detected == case["expected"],
            "classification": None,  # filled below
        })

    # Phase 4: Classify all FNs
    print("\n[Phase 4] Classifying failures...")

    # Include seeds too
    all_with_seeds = []
    for case_name, v in seed_results.items():
        if v["is_positive"]:
            all_with_seeds.append({
                "name": case_name,
                "pattern": v["pattern"],
                "is_seed": True,
                "detected": v["detected"],
                "expected": True,
                "correct": v["detected"],
                "seed_name": None,
                "seed_detected": None,
                "variant_type": "seed",
            })
    
    all_with_seeds.extend(case_results)

    # Classification
    categories = {
        "seed_failure": 0,           # original seed failed
        "inherited": 0,             # seed failed, variant inherited
        "true_naming": 0,           # seed passed, naming variant failed
        "true_expression": 0,       # seed passed, expression variant failed
        "true_loop_form": 0,        # seed passed, loop form variant failed
        "true_class_structure": 0,  # seed passed, class variant failed
        "true_other": 0,            # seed passed, other variant failed
    }

    # Per-detector tracking
    per_detector = defaultdict(lambda: {
        "total": 0, "tp": 0, "fp": 0, "fn": 0, "tn": 0,
        "categories": defaultdict(int),
        "seed_passing": 0, "seed_failing": 0,
        "variant_passing": 0, "variant_failing": 0,
        "variant_passing_from_passing_seed": 0,
        "variant_failing_from_passing_seed": 0,
    })

    for c in all_with_seeds:
        pid = c["pattern"]
        d = per_detector[pid]
        d["total"] += 1

        is_positive = c["expected"]
        detected = c["detected"]

        if is_positive and detected:
            d["tp"] += 1
        elif is_positive and not detected:
            d["fn"] += 1
        elif not is_positive and detected:
            d["fp"] += 1
        elif not is_positive and not detected:
            d["tn"] += 1

        if c["is_seed"]:
            if c["detected"]:
                d["seed_passing"] += 1
            else:
                d["seed_failing"] += 1
        else:
            if c["detected"]:
                d["variant_passing"] += 1
            else:
                d["variant_failing"] += 1

            # Classify variant FNs
            if not c["detected"] and c["expected"]:
                if c["seed_detected"] == False:
                    categories["inherited"] += 1
                    d["categories"]["inherited"] += 1
                elif c["seed_detected"] == True:
                    vt = c["variant_type"]
                    if vt == "naming":
                        categories["true_naming"] += 1
                        d["categories"]["true_naming"] += 1
                    elif vt == "expr":
                        categories["true_expression"] += 1
                        d["categories"]["true_expression"] += 1
                    elif vt == "loop":
                        categories["true_loop_form"] += 1
                        d["categories"]["true_loop_form"] += 1
                    elif vt == "class":
                        categories["true_class_structure"] += 1
                        d["categories"]["true_class_structure"] += 1
                    else:
                        categories["true_other"] += 1
                        d["categories"]["true_other"] += 1

    # Also count seed failures
    for c in all_with_seeds:
        if c["is_seed"] and not c["detected"] and c["expected"]:
            categories["seed_failure"] += 1
            pid = c["pattern"]
            per_detector[pid]["categories"]["seed_failure"] += 1

    # Phase 5: Report
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    total_fn = sum(categories.values())
    total_tp = sum(d["tp"] for d in per_detector.values())
    total_fp = sum(d["fp"] for d in per_detector.values())
    total_tn = sum(d["tn"] for d in per_detector.values())
    total_fn_check = sum(d["fn"] for d in per_detector.values())
    total_positive = total_tp + total_fn_check
    
    precision = total_tp / (total_tp + total_fp) * 100 if (total_tp + total_fp) > 0 else 0
    recall = total_tp / (total_tp + total_fn_check) * 100 if (total_tp + total_fn_check) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    case_level_recall = seeds_passing / len(positive_seeds) * 100 if positive_seeds else 0

    print(f"\nOVERALL METRICS:")
    print(f"  Total cases: {total_tp + total_fn_check + total_fp + total_tn}")
    print(f"  TP: {total_tp}, FP: {total_fp}, FN: {total_fn_check}, TN: {total_tn}")
    print(f"  Pattern-level precision: {precision:.1f}%")
    print(f"  Pattern-level recall:    {recall:.1f}%")
    print(f"  Pattern-level F1:        {f1:.1f}%")
    print(f"  Case-level recall (seeds only): {case_level_recall:.1f}% ({seeds_passing}/{len(positive_seeds)} seeds pass)")

    print(f"\nFAILURE CLASSIFICATION (all {total_fn_check} FN):")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        pct = count / total_fn_check * 100 if total_fn_check > 0 else 0
        print(f"  {cat:<30} {count:>4}  ({pct:.1f}%)")
    
    # Verification
    accounted = sum(categories.values())
    print(f"\n  Sum of categories: {accounted}")
    print(f"  Total FN: {total_fn_check}")
    assert accounted == total_fn_check, f"MISMATCH: {accounted} != {total_fn_check}"
    print(f"  Verified: categories sum to total FN")

    # Derived breakdown
    seed_level_fn = categories["seed_failure"]
    inherited_fn = categories["inherited"]
    true_variant_fn = categories["true_naming"] + categories["true_expression"] + categories["true_loop_form"] + categories["true_class_structure"] + categories["true_other"]
    
    print(f"\nDERIVED BREAKDOWN:")
    print(f"  Seed-level failures (detector can't handle the original code): {seed_level_fn}")
    print(f"  Inherited failures (variant of failing seed):                {inherited_fn}")
    print(f"  True variant failures (seed passed, variant broke it):        {true_variant_fn}")
    print(f"  Sum check: {seed_level_fn} + {inherited_fn} + {true_variant_fn} = {seed_level_fn + inherited_fn + true_variant_fn}")

    # Recoverable analysis
    print(f"\nRECOVERABLE FN ANALYSIS:")
    naming_recoverable = categories["true_naming"]
    expr_recoverable = categories["true_expression"]
    loop_recoverable = categories["true_loop_form"]
    class_recoverable = categories["true_class_structure"]
    other_recoverable = categories["true_other"]
    seed_recoverable = seed_level_fn  # recoverable only by fixing detector logic
    inherited_not_recoverable = inherited_fn  # NOT directly recoverable -- must fix seed first
    
    total_recoverable = naming_recoverable + expr_recoverable + loop_recoverable + class_recoverable + other_recoverable
    print(f"  True variant-caused (directly recoverable by variant-level fixes): {total_recoverable}")
    print(f"    naming:      {naming_recoverable}")
    print(f"    expression:  {expr_recoverable}")
    print(f"    loop form:   {loop_recoverable}")
    print(f"    class:       {class_recoverable}")
    print(f"    other:       {other_recoverable}")
    print(f"  Seed-level failures (recoverable only by fixing detector heuristics): {seed_recoverable}")
    print(f"  Inherited (NOT directly recoverable -- blocked by seed failure):     {inherited_not_recoverable}")

    # Projected improvements
    print(f"\nPROJECTED RECALL IMPROVEMENTS:")
    base_tp = total_tp
    base_fn = total_fn_check
    
    # If we fix naming variants
    tp_after_naming = base_tp + naming_recoverable
    fn_after_naming = base_fn - naming_recoverable
    recall_after_naming = tp_after_naming / (tp_after_naming + fn_after_naming) * 100
    print(f"  Fix naming variants:          recall {recall:.1f}% -> {recall_after_naming:.1f}%  (fix {naming_recoverable} FN)")
    
    # If we also fix expression variants
    tp_after_expr = tp_after_naming + expr_recoverable
    fn_after_expr = fn_after_naming - expr_recoverable
    recall_after_expr = tp_after_expr / (tp_after_expr + fn_after_expr) * 100
    print(f"  + fix expression variants:    recall {recall_after_naming:.1f}% -> {recall_after_expr:.1f}%  (fix {expr_recoverable} FN)")
    
    # If we also fix loop-form variants
    tp_after_loop = tp_after_expr + loop_recoverable
    fn_after_loop = fn_after_expr - loop_recoverable
    recall_after_loop = tp_after_loop / (tp_after_loop + fn_after_loop) * 100
    print(f"  + fix loop-form variants:     recall {recall_after_expr:.1f}% -> {recall_after_loop:.1f}%  (fix {loop_recoverable} FN)")
    
    # If we also fix class-structure variants
    tp_after_class = tp_after_loop + class_recoverable
    fn_after_class = fn_after_loop - class_recoverable
    recall_after_class = tp_after_class / (tp_after_class + fn_after_class) * 100
    print(f"  + fix class-structure:        recall {recall_after_loop:.1f}% -> {recall_after_class:.1f}%  (fix {class_recoverable} FN)")
    
    # If we also fix seed-level failures
    tp_after_seeds = tp_after_class + seed_recoverable
    fn_after_seeds = fn_after_class - seed_recoverable
    recall_after_seeds = tp_after_seeds / (tp_after_seeds + fn_after_seeds) * 100
    print(f"  + fix seed-level failures:    recall {recall_after_class:.1f}% -> {recall_after_seeds:.1f}%  (fix {seed_recoverable} FN)")
    
    print(f"\n  REMAINING (inherited, not directly fixable): {inherited_not_recoverable} FN")
    remaining_fn = fn_after_seeds
    remaining_recall = tp_after_seeds / (tp_after_seeds + remaining_fn) * 100
    print(f"  Realistic ceiling (all variant + seed fixes): recall ~ {remaining_recall:.1f}% ({tp_after_seeds} TP, {remaining_fn} remaining FN)")

    # Per-detector detail
    print(f"\n{'='*70}")
    print("PER-DETECTOR DETAIL")
    print(f"{'='*70}")
    for pid in sorted(per_detector.keys()):
        d = per_detector[pid]
        if d["total"] == 0:
            continue
        det_prec = d["tp"] / (d["tp"] + d["fp"]) * 100 if (d["tp"] + d["fp"]) > 0 else 0
        det_rec = d["tp"] / (d["tp"] + d["fn"]) * 100 if (d["tp"] + d["fn"]) > 0 else 0
        
        cats = d["categories"]
        print(f"\n  {pid}:")
        print(f"    Cases: {d['total']}, TP: {d['tp']}, FP: {d['fp']}, FN: {d['fn']}, TN: {d['tn']}")
        print(f"    Precision: {det_prec:.1f}%, Recall: {det_rec:.1f}%")
        print(f"    Seeds: {d['seed_passing']} pass / {d['seed_failing']} fail")
        print(f"    Variants: {d['variant_passing']} pass / {d['variant_failing']} fail")
        if cats:
            print(f"    FN causes:")
            for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
                print(f"      {cat}: {cnt}")

    # Save results
    output = {
        "overall": {
            "total_cases": total_tp + total_fn_check + total_fp + total_tn,
            "tp": total_tp, "fp": total_fp, "fn": total_fn_check, "tn": total_tn,
            "precision_pct": round(precision, 2),
            "recall_pct": round(recall, 2),
            "f1_pct": round(f1, 2),
            "case_level_recall_pct": round(case_level_recall, 2),
            "seeds_passing": seeds_passing,
            "seeds_total": len(positive_seeds),
        },
        "failure_classification": dict(categories),
        "derived": {
            "seed_level_fn": seed_level_fn,
            "inherited_fn": inherited_fn,
            "true_variant_fn": true_variant_fn,
        },
        "recoverable": {
            "true_naming": naming_recoverable,
            "true_expression": expr_recoverable,
            "true_loop_form": loop_recoverable,
            "true_class_structure": class_recoverable,
            "true_other": other_recoverable,
            "seed_level": seed_recoverable,
            "inherited_not_recoverable": inherited_not_recoverable,
            "total_directly_recoverable": total_recoverable,
        },
        "projected": {
            "after_naming_fix": round(recall_after_naming, 2),
            "after_naming_plus_expr": round(recall_after_expr, 2),
            "after_all_variant_fixes": round(recall_after_loop, 2),
            "after_seed_fixes": round(recall_after_seeds, 2),
            "ceiling_fn": remaining_fn,
        },
        "per_detector": {pid: {k: v for k, v in d.items() if k != "categories"} 
                         for pid, d in per_detector.items()},
        "per_detector_categories": {pid: dict(d["categories"]) 
                                     for pid, d in per_detector.items() if d["categories"]},
    }
    
    with open("deep_failure_analysis.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nResults saved to deep_failure_analysis.json")


if __name__ == "__main__":
    main()
