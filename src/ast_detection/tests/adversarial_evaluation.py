"""Adversarial Evaluation Harness for PathForge AST Detectors.

Generates naming variants, structural variants, and expression variants
from existing seed cases. Runs everything through the AST engine and
produces per-detector metrics with failure classification.

Usage:
    python -m src.ast_detection.tests.adversarial_evaluation
"""

import ast
import re
import sys
import json
from collections import defaultdict
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, field

from src.ast_detection.run_analysis import ASTAnalysisEngine
from src.ast_detection.registry import get_all_detectors
from src.ast_detection.detector_interface import DetectionResult

# ============================================================================
# VARIANT GENERATORS
# ============================================================================

# Common variable name mappings for renaming variants
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


def rename_variables(code: str, rename_map: Dict[str, str]) -> str:
    """Rename variables in code according to a mapping."""
    result = code
    for old_name, new_name in rename_map.items():
        # Word-boundary replacement to avoid partial matches
        result = re.sub(r'\b' + re.escape(old_name) + r'\b', new_name, result)
    return result


def generate_naming_variants(code: str) -> List[Tuple[str, str]]:
    """Generate naming variants of code."""
    variants = []
    for map_name, name_map in RENAME_MAPS.items():
        for old_name, new_names in name_map.items():
            for new_name in new_names[:2]:  # Limit to 2 variants per name
                if old_name in code:
                    renamed = rename_variables(code, {old_name: new_name})
                    if renamed != code:
                        variants.append((f"rename_{map_name}_{old_name}_{new_name}", renamed))
    return variants


def generate_loop_form_variants(code: str) -> List[Tuple[str, str]]:
    """Generate while/for loop form variants where semantically safe."""
    variants = []
    # Convert simple for-range loops to while loops
    # Pattern: for i in range(N): ... → i=0; while i < N: ...; i+=1
    range_pattern = re.compile(
        r'for (\w+) in range\(([^)]+)\):\s*\n((?:    .+\n?)+)',
        re.MULTILINE
    )
    for match in range_pattern.finditer(code):
        var_name = match.group(1)
        range_arg = match.group(2)
        body = match.group(3)
        # Only convert simple range(N) or range(start, end)
        if ',' not in range_arg:
            while_version = f"{var_name} = 0\nwhile {var_name} < {range_arg}:\n{body}    {var_name} += 1\n"
            variants.append(("while_simple", while_version))

    # Convert for-in-collection to while with index
    for_pattern = re.compile(
        r'for (\w+) in (\w+):\s*\n((?:    .+\n?)+)',
        re.MULTILINE
    )
    for match in for_pattern.finditer(code):
        var_name = match.group(1)
        collection = match.group(2)
        body = match.group(3)
        # Replace variable references in body
        new_var = f"_idx_{var_name}"
        body_renamed = body.replace(var_name, f"{collection}[{new_var}]")
        while_version = f"{new_var} = 0\nwhile {new_var} < len({collection}):\n{body_renamed}    {new_var} += 1\n"
        variants.append(("while_collection", while_version))

    return variants


def generate_expression_variants(code: str) -> List[Tuple[str, str]]:
    """Generate equivalent expression variants."""
    variants = []

    # Midpoint variants
    midpoint_patterns = [
        (r'\(left \+ right\) // 2', 'left + (right - left) // 2'),
        (r'\(lo \+ hi\) // 2', 'lo + (hi - lo) // 2'),
        (r'\(low \+ high\) // 2', 'low + (high - low) // 2'),
        (r'\(l \+ r\) // 2', 'l + (r - l) // 2'),
    ]
    for pattern, replacement in midpoint_patterns:
        if re.search(pattern, code):
            variants.append(("midpoint_variant", re.sub(pattern, replacement, code)))

    # Comparison variants
    comparison_variants = [
        (r'(\w+) < (\w+)', r'not (\1 >= \2)'),
        (r'(\w+) > (\w+)', r'not (\1 <= \2)'),
        (r'(\w+) == (\w+)', r'not (\1 != \2)'),
        (r'(\w+) != (\w+)', r'not (\1 == \2)'),
    ]
    # Only generate negated comparison variants for simple cases
    for pattern, replacement in comparison_variants[:2]:
        matches = list(re.finditer(pattern, code))
        if matches and len(matches) <= 3:  # Don't do this for code with many comparisons
            m = matches[0]
            variant = code[:m.start()] + re.sub(pattern, replacement, code[m.start():m.end()]) + code[m.end():]
            if variant != code:
                variants.append(("negated_comparison", variant))

    # Arithmetic variants
    if '+= 1' in code:
        variants.append(("increment_variant", code.replace('+= 1', '= _idx + 1', 1).replace('_idx', '___tmp', 1) + ''))
        # Simpler: just replace one increment
        variant = code.replace('+= 1', '+= 1  # incremented', 1)
        if variant != code:
            pass  # Skip comment-only changes

    return variants


def generate_helper_function_variant(code: str) -> List[Tuple[str, str]]:
    """Extract a loop body into a helper function."""
    variants = []

    # Find simple for loops and extract body
    pattern = re.compile(
        r'((?:def \w+\([^)]*\):\s*\n(?:    .+\n)*?)(    for (\w+) in ([^:]+):\s*\n)((?:        .+\n?)+))',
        re.MULTILINE
    )
    for match in pattern.finditer(code):
        full_match = match.group(0)
        func_def_line = match.group(1)
        for_line = match.group(4)
        loop_var = match.group(5)
        collection = match.group(6)
        body = match.group(7)

        # This is complex; skip for now to avoid breaking code
        pass

    return variants


def generate_class_based_variant(code: str) -> List[Tuple[str, str]]:
    """Wrap standalone function in a class method."""
    variants = []
    # Find top-level function definitions
    func_pattern = re.compile(r'^(def (\w+)\([^)]*\):\s*\n(?:    .+\n?)+)', re.MULTILINE)
    for match in func_pattern.finditer(code):
        func_name = match.group(1)
        # Extract body from the match
        body_match = re.search(r':\s*\n((?:    .+\n?)+)', match.group(0))
        if not body_match:
            continue
        body = body_match.group(1)
        # Extract params
        params_match = re.search(r'def \w+\(([^)]*)\)', match.group(0))
        params = params_match.group(1) if params_match else ''
        if 'class ' not in code:  # Only if not already in a class
            class_code = f"class Solution:\n    def {func_name}(self, {params}):\n{body}"
            variants.append((f"class_{func_name}", class_code))

    return variants


def generate_comprehensive_variants(code: str) -> List[Tuple[str, str]]:
    """Generate all variant types for a given code snippet."""
    all_variants = []

    # Naming variants (highest volume)
    for name, variant_code in generate_naming_variants(code):
        all_variants.append((f"naming_{name}", variant_code))

    # Loop form variants
    for name, variant_code in generate_loop_form_variants(code):
        all_variants.append((f"loop_{name}", variant_code))

    # Expression variants
    for name, variant_code in generate_expression_variants(code):
        all_variants.append((f"expr_{name}", variant_code))

    # Class-based variants
    for name, variant_code in generate_class_based_variant(code):
        all_variants.append((f"class_{name}", variant_code))

    return all_variants


# ============================================================================
# EVALUATION ENGINE
# ============================================================================

@dataclass
class TestCase:
    name: str
    code: str
    expected_pattern: str
    expected_detected: bool  # True = should detect, False = should NOT detect
    variant_type: str = "seed"
    failure_cause: str = ""


@dataclass
class EvaluationResult:
    test_case: TestCase
    detected: bool
    confidence: float
    pattern_id: str
    correct: bool
    failure_cause: str = ""


class AdversarialEvaluator:
    def __init__(self):
        self.engine = ASTAnalysisEngine()
        self.detectors = {d.pattern_id: d for d in get_all_detectors()}
        self.results: List[EvaluationResult] = []

    def run_single_detector(self, detector, code: str) -> DetectionResult:
        """Run a single detector on code and return its DetectionResult."""
        try:
            ast_root = ast.parse(code)
            return detector.detect(ast_root)
        except (SyntaxError, ValueError):
            return DetectionResult(
                pattern_id=detector.pattern_id,
                confidence=0.0,
                evidence=[],
                detected=False
            )

    def evaluate_case(self, case: TestCase) -> EvaluationResult:
        """Evaluate a single test case against its expected detector."""
        detector = self.detectors.get(case.expected_pattern)
        if not detector:
            return EvaluationResult(
                test_case=case,
                detected=False,
                confidence=0.0,
                pattern_id=case.expected_pattern,
                correct=False,
                failure_cause="taxonomy_orphan"
            )

        result = self.run_single_detector(detector, case.code)

        detected = result.confidence > 0.0 and result.detected
        correct = detected == case.expected_detected

        failure_cause = ""
        if not correct:
            if case.expected_detected and not detected:
                failure_cause = self.classify_false_negative(case, result)
            elif not case.expected_detected and detected:
                failure_cause = "false_positive"

        return EvaluationResult(
            test_case=case,
            detected=detected,
            confidence=result.confidence,
            pattern_id=result.pattern_id,
            correct=correct,
            failure_cause=failure_cause
        )

    def classify_false_negative(self, case: TestCase, result: DetectionResult) -> str:
        """Classify the cause of a false negative."""
        vt = case.variant_type
        if vt.startswith("naming_"):
            return "naming_dependence"
        elif vt.startswith("loop_"):
            return "ast_shape_dependence"
        elif vt.startswith("expr_"):
            return "expression_dependence"
        elif vt.startswith("class_"):
            return "class_structure_dependence"
        elif vt == "seed":
            return "insufficient_structural_reasoning"
        else:
            return "insufficient_structural_reasoning"

    def run_full_evaluation(self, corpus: List[TestCase]) -> Dict[str, Any]:
        """Run the full adversarial evaluation."""
        per_detector = defaultdict(lambda: {
            "tp": 0, "fp": 0, "fn": 0, "tn": 0,
            "cases": [], "failure_causes": defaultdict(int),
            "confidences": [], "variant_failures": defaultdict(int),
        })

        for case in corpus:
            result = self.evaluate_case(case)
            self.results.append(result)

            d = per_detector[case.expected_pattern]
            d["cases"].append(result)

            if result.correct:
                if case.expected_detected:
                    d["tp"] += 1
                else:
                    d["tn"] += 1
            else:
                if case.expected_detected and not result.detected:
                    d["fn"] += 1
                    d["failure_causes"][result.failure_cause] += 1
                    d["variant_failures"][case.variant_type.split("_")[0]] += 1
                elif not case.expected_detected and result.detected:
                    d["fp"] += 1

            if result.detected:
                d["confidences"].append(result.confidence)

        return dict(per_detector)


# ============================================================================
# SEED DATA EXTRACTION
# ============================================================================

def extract_seeds_from_existing_tests() -> List[TestCase]:
    """Extract positive and negative cases from existing test files."""
    cases = []

    # Import existing validation data
    try:
        from src.ast_detection.tests.validate_all_36_detectors import VALIDATION_CORPUS
    except ImportError:
        print("WARNING: Could not import VALIDATION_CORPUS, using empty corpus")
        return cases

    for pattern_id, (positives, negatives) in VALIDATION_CORPUS.items():
        for name, code in positives:
            cases.append(TestCase(
                name=name,
                code=code,
                expected_pattern=pattern_id,
                expected_detected=True,
                variant_type="seed"
            ))
        for name, code in negatives:
            cases.append(TestCase(
                name=name,
                code=code,
                expected_pattern=pattern_id,
                expected_detected=False,
                variant_type="seed"
            ))

    return cases


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run_adversarial_evaluation():
    """Run the complete adversarial evaluation."""
    print("=" * 70)
    print("PATHFORGE AST ADVERSARIAL EVALUATION")
    print("=" * 70)

    evaluator = AdversarialEvaluator()

    # Step 1: Extract seed cases
    print("\n[1/4] Extracting seed cases from existing tests...")
    seed_cases = extract_seeds_from_existing_tests()
    print(f"  Extracted {len(seed_cases)} seed cases")

    # Step 2: Generate variants
    print("\n[2/4] Generating adversarial variants...")
    all_cases = list(seed_cases)  # Start with seeds
    positive_seeds = [c for c in seed_cases if c.expected_detected]

    for case in positive_seeds:
        variants = generate_comprehensive_variants(case.code)
        for variant_type, variant_code in variants:
            # Validate the variant parses
            try:
                ast.parse(variant_code)
                all_cases.append(TestCase(
                    name=f"{case.name}_{variant_type}",
                    code=variant_code,
                    expected_pattern=case.expected_pattern,
                    expected_detected=True,
                    variant_type=variant_type
                ))
            except SyntaxError:
                pass  # Skip variants that don't parse

    total_variants = len(all_cases) - len(seed_cases)
    print(f"  Generated {total_variants} variants from {len(positive_seeds)} positive seeds")
    print(f"  Total test cases: {len(all_cases)}")

    # Step 3: Run evaluation
    print("\n[3/4] Running adversarial evaluation...")
    per_detector = evaluator.run_full_evaluation(all_cases)
    print(f"  Evaluated {len(evaluator.results)} cases across {len(per_detector)} detectors")

    # Step 4: Generate report
    print("\n[4/4] Generating report...")
    report = generate_report(per_detector, len(seed_cases), total_variants, all_cases)

    # Save detailed results
    with open("adversarial_evaluation_results.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n  Detailed results saved to adversarial_evaluation_results.json")

    # Print summary
    print_summary(report)

    return report


def generate_report(per_detector: dict, seed_count: int, variant_count: int, all_cases: List[TestCase]) -> dict:
    """Generate a structured evaluation report."""
    report = {
        "summary": {
            "total_cases": len(all_cases),
            "seed_cases": seed_count,
            "variant_cases": variant_count,
            "detectors_evaluated": len(per_detector),
        },
        "per_detector": {},
        "failure_taxonomy": defaultdict(int),
        "naming_sensitivity": {},
        "structural_sensitivity": {},
    }

    overall_tp = overall_fp = overall_fn = overall_tn = 0

    for pattern_id, data in sorted(per_detector.items()):
        tp, fp, fn, tn = data["tp"], data["fp"], data["fn"], data["tn"]
        overall_tp += tp
        overall_fp += fp
        overall_fn += fn
        overall_tn += tn

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        # Variant-specific analysis
        naming_fails = sum(v for k, v in data["failure_causes"].items() if "naming" in k)
        structural_fails = sum(v for k, v in data["failure_causes"].items() if "shape" in k or "structure" in k)
        expression_fails = sum(v for k, v in data["failure_causes"].items() if "expression" in k)

        # Naming sensitivity: what % of naming variants failed?
        naming_cases = [c for c in data["cases"] if c.test_case.variant_type.startswith("naming_")]
        naming_failures = sum(1 for c in naming_cases if not c.correct)
        naming_sensitivity = naming_failures / len(naming_cases) if naming_cases else 0.0

        # Structural sensitivity
        structural_cases = [c for c in data["cases"] if c.test_case.variant_type.startswith(("loop_", "class_"))]
        structural_failures = sum(1 for c in structural_cases if not c.correct)
        structural_sensitivity = structural_failures / len(structural_cases) if structural_cases else 0.0

        avg_confidence = sum(data["confidences"]) / len(data["confidences"]) if data["confidences"] else 0.0

        report["per_detector"][pattern_id] = {
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "avg_confidence": round(avg_confidence, 4),
            "naming_sensitivity": round(naming_sensitivity, 4),
            "structural_sensitivity": round(structural_sensitivity, 4),
            "failure_causes": dict(data["failure_causes"]),
            "total_cases": len(data["cases"]),
        }

        for cause, count in data["failure_causes"].items():
            report["failure_taxonomy"][cause] += count

        report["naming_sensitivity"][pattern_id] = round(naming_sensitivity, 4)
        report["structural_sensitivity"][pattern_id] = round(structural_sensitivity, 4)

    # Overall metrics
    overall_precision = overall_tp / (overall_tp + overall_fp) if (overall_tp + overall_fp) > 0 else 0.0
    overall_recall = overall_tp / (overall_tp + overall_fn) if (overall_tp + overall_fn) > 0 else 0.0
    overall_f1 = 2 * overall_precision * overall_recall / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0.0

    report["overall"] = {
        "tp": overall_tp, "fp": overall_fp, "fn": overall_fn, "tn": overall_tn,
        "precision": round(overall_precision, 4),
        "recall": round(overall_recall, 4),
        "f1": round(overall_f1, 4),
    }

    report["failure_taxonomy"] = dict(report["failure_taxonomy"])

    return report


def print_summary(report: dict):
    """Print a summary of the evaluation results."""
    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)

    o = report["overall"]
    print(f"\nOverall Metrics:")
    print(f"  Precision: {o['precision']:.1%}  ({o['tp']} TP, {o['fp']} FP)")
    print(f"  Recall:    {o['recall']:.1%}  ({o['tp']} TP, {o['fn']} FN)")
    print(f"  F1:        {o['f1']:.1%}")
    print(f"  True Neg:  {o['tn']}")

    print(f"\nFailure Taxonomy:")
    for cause, count in sorted(report["failure_taxonomy"].items(), key=lambda x: -x[1]):
        print(f"  {cause}: {count}")

    print(f"\nPer-Detector Metrics (sorted by recall):")
    print(f"  {'Pattern':<30} {'Prec':>6} {'Rec':>6} {'F1':>6} {'Name%':>6} {'Struct%':>7}")
    print(f"  {'-'*30} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*7}")

    for pid, data in sorted(report["per_detector"].items(), key=lambda x: x[1]["recall"]):
        ns = report["naming_sensitivity"].get(pid, 0)
        ss = report["structural_sensitivity"].get(pid, 0)
        print(f"  {pid:<30} {data['precision']:>6.1%} {data['recall']:>6.1%} {data['f1']:>6.1%} {ns:>6.1%} {ss:>7.1%}")

    # Highest risk detectors
    print(f"\nHighest-Risk Detectors (lowest recall):")
    risk_list = sorted(report["per_detector"].items(), key=lambda x: x[1]["recall"])
    for pid, data in risk_list[:5]:
        causes = data["failure_causes"]
        cause_str = ", ".join(f"{k}:{v}" for k, v in sorted(causes.items(), key=lambda x: -x[1]))
        print(f"  {pid}: recall={data['recall']:.1%}, causes=[{cause_str}]")

    # Most name-sensitive detectors
    print(f"\nMost Name-Sensitive Detectors:")
    name_sensitive = sorted(report["naming_sensitivity"].items(), key=lambda x: -x[1])
    for pid, sensitivity in name_sensitive[:5]:
        if sensitivity > 0:
            print(f"  {pid}: {sensitivity:.1%} of naming variants failed")

    # Most structurally sensitive detectors
    print(f"\nMost Structurally Sensitive Detectors:")
    struct_sensitive = sorted(report["structural_sensitivity"].items(), key=lambda x: -x[1])
    for pid, sensitivity in struct_sensitive[:5]:
        if sensitivity > 0:
            print(f"  {pid}: {sensitivity:.1%} of structural variants failed")


if __name__ == "__main__":
    report = run_adversarial_evaluation()
