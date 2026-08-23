"""Semantic Experiment 1D: Generalization validation corpus.

Builds 150+ cases from the existing 571-case validation corpus,
supplemented by generated adversarial variants (renaming, loop forms,
class wrapping). The corpus is disjoint from the 46-case calibration set.

Patterns of interest: array_traversal, hash_map_lookup, prefix_sum,
two_pointers_opposite. Binary search cases included for observation only.
"""
import ast
import re
import sys
import os
from dataclasses import dataclass
from typing import List, Tuple, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))


@dataclass
class EvalCase:
    name: str
    code: str
    expected_pattern: str
    is_positive: bool
    source: str  # "seed", "rename", "loop_form", "class_wrap", "cross_pattern_neg"
    notes: str = ""


# ---------------------------------------------------------------------------
# Renaming helper
# ---------------------------------------------------------------------------

RENAME_MAPS = {
    "idx": {"i": ["idx", "index", "pos", "p"], "j": ["idx2", "index2", "pos2", "q"]},
    "data": {"nums": ["data", "arr", "elements", "values"], "arr": ["data", "nums", "elements"]},
    "pointers": {"left": ["lo", "start", "l", "low"], "right": ["hi", "end", "r", "high"]},
}


def rename_variables(code: str, mapping: Dict[str, str]) -> str:
    result = code
    for old, new in mapping.items():
        result = re.sub(r'\b' + re.escape(old) + r'\b', new, result)
    return result


def generate_rename_variants(code: str) -> List[Tuple[str, str]]:
    variants = []
    for map_name, name_map in RENAME_MAPS.items():
        for old_name, new_names in list(name_map.items())[:2]:
            for new_name in new_names[:2]:
                if re.search(r'\b' + re.escape(old_name) + r'\b', code):
                    renamed = rename_variables(code, {old_name: new_name})
                    if renamed != code:
                        variants.append((f"rename_{map_name}_{old_name}_{new_name}", renamed))
    return variants


def generate_while_variant(code: str) -> List[Tuple[str, str]]:
    """Convert a simple for-range loop to a while loop."""
    variants = []
    pattern = re.compile(
        r'for (\w+) in range\(([^)]+)\):\s*\n((?:    .+\n?)+)',
        re.MULTILINE
    )
    for match in pattern.finditer(code):
        var = match.group(1)
        bound = match.group(2)
        body = match.group(3)
        if ',' not in bound:
            while_code = f"{var} = 0\nwhile {var} < {bound}:\n{body}    {var} += 1\n"
            variants.append(("while_from_for", while_code))
    return variants


def generate_class_variant(code: str) -> List[Tuple[str, str]]:
    """Wrap a function in a class method."""
    variants = []
    func_match = re.search(r'^def (\w+)\(([^)]*)\):\s*\n((?:    .+\n?)+)', code, re.MULTILINE)
    if func_match and 'class ' not in code:
        name = func_match.group(1)
        params = func_match.group(2)
        body = func_match.group(3)
        class_code = f"class Solution:\n    def {name}(self, {params}):\n{body}"
        variants.append(("class_wrap", class_code))
    return variants


# ---------------------------------------------------------------------------
# Build the corpus
# ---------------------------------------------------------------------------

def build_corpus() -> List[EvalCase]:
    """Build the evaluation corpus."""
    from src.ast_detection.tests.validate_all_36_detectors import VALIDATION_CORPUS

    target_patterns = {
        "array_traversal", "hash_map_lookup", "prefix_sum",
        "two_pointers_opposite",
    }

    # Additional patterns used as cross-pattern negatives
    cross_pattern_neg_patterns = {
        "binary_search_standard", "binary_search_answer",
        "sorting", "brute_force",
    }

    cases = []

    # ---- 1. Seed cases for target patterns ----
    for pid in target_patterns:
        if pid not in VALIDATION_CORPUS:
            continue
        positives, negatives = VALIDATION_CORPUS[pid]

        for name, code in positives:
            cases.append(EvalCase(
                name=f"{pid}_{name}",
                code=code,
                expected_pattern=pid,
                is_positive=True,
                source="seed",
            ))

        for name, code in negatives:
            cases.append(EvalCase(
                name=f"{pid}_{name}_neg",
                code=code,
                expected_pattern=pid,
                is_positive=False,
                source="seed",
            ))

    # ---- 2. Cross-pattern negatives ----
    # Code that is clearly NOT one of the target patterns
    for pid in cross_pattern_neg_patterns:
        if pid not in VALIDATION_CORPUS:
            continue
        positives, _ = VALIDATION_CORPUS[pid]
        for name, code in positives[:3]:  # Limit to 3 per cross-pattern
            for target in target_patterns:
                cases.append(EvalCase(
                    name=f"cross_{pid}_{name}_vs_{target}",
                    code=code,
                    expected_pattern=target,
                    is_positive=False,
                    source="cross_pattern_neg",
                    notes=f"Code is {pid}, not {target}",
                ))

    # ---- 3. Generate adversarial variants from positive seeds ----
    positive_seeds = [c for c in cases if c.is_positive and c.source == "seed"]
    for case in positive_seeds:
        # Rename variants
        for vname, vcode in generate_rename_variants(case.code):
            try:
                ast.parse(vcode)
                cases.append(EvalCase(
                    name=f"{case.name}_{vname}",
                    code=vcode,
                    expected_pattern=case.expected_pattern,
                    is_positive=True,
                    source="rename",
                ))
            except SyntaxError:
                pass

        # While-loop variant
        for vname, vcode in generate_while_variant(case.code):
            try:
                ast.parse(vcode)
                cases.append(EvalCase(
                    name=f"{case.name}_{vname}",
                    code=vcode,
                    expected_pattern=case.expected_pattern,
                    is_positive=True,
                    source="loop_form",
                ))
            except SyntaxError:
                pass

        # Class-wrap variant
        for vname, vcode in generate_class_variant(case.code):
            try:
                ast.parse(vcode)
                cases.append(EvalCase(
                    name=f"{case.name}_{vname}",
                    code=vcode,
                    expected_pattern=case.expected_pattern,
                    is_positive=True,
                    source="class_wrap",
                ))
            except SyntaxError:
                pass

    return cases


def get_corpus_stats(cases: List[EvalCase]) -> dict:
    stats = {}
    for c in cases:
        if c.expected_pattern not in stats:
            stats[c.expected_pattern] = {"pos": 0, "neg": 0, "sources": {}}
        if c.is_positive:
            stats[c.expected_pattern]["pos"] += 1
        else:
            stats[c.expected_pattern]["neg"] += 1
        src = c.source
        if src not in stats[c.expected_pattern]["sources"]:
            stats[c.expected_pattern]["sources"][src] = 0
        stats[c.expected_pattern]["sources"][src] += 1
    return stats
