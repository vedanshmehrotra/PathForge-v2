"""Detector for backtracking permutation generation pattern.

Detects recursive permutation generation algorithms using either:
1. Swap/recurse/swap pattern (in-place permutation)
2. Visited-array pattern (used-element tracking)

Does NOT detect:
- Subset generation (append/pop based)
- Ordinary recursion without permutation-specific patterns
- Iterative permutation generation
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class BacktrackingPermutationDetector(BaseDetector):
    pattern_id = "backtracking_permutation"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_backtracking_permutation(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_swap_recurse_swap = any(e.type == "swap_recurse_swap" for e in evidence)
        has_visited_array = any(e.type == "visited_array" for e in evidence)
        has_permutation = any(e.type == "permutation_generation" for e in evidence)
        has_exploration = any(e.type == "recursive_exploration" for e in evidence)

        detected = has_swap_recurse_swap or (has_visited_array and has_permutation)

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_backtracking_permutation(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.FunctionDef):
                continue

            func_name = node.name

            if not self._has_recursive_call(node, func_name):
                continue

            has_swap = self._find_swap_recurse_swap(node, func_name)
            has_visited = self._find_visited_array(node)
            has_perm = self._find_permutation_generation(node)
            has_explore = self._find_recursive_exploration(node, func_name)

            if not (has_swap or has_visited):
                continue

            if has_swap:
                evidence.append(
                    EvidenceItem(
                        type="swap_recurse_swap",
                        description="Swap/recurse/swap pattern for in-place permutation",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.35,
                    )
                )

            if has_visited:
                evidence.append(
                    EvidenceItem(
                        type="visited_array",
                        description="Visited/used boolean array for tracking selected elements",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

            if has_perm:
                evidence.append(
                    EvidenceItem(
                        type="permutation_generation",
                        description="Building permutation result by appending elements",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

            if has_explore:
                evidence.append(
                    EvidenceItem(
                        type="recursive_exploration",
                        description="Recursive call with incremented index",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
                    )
                )

    def _has_recursive_call(self, func_def: ast.FunctionDef, func_name: str) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == func_name:
                    return True
        return False

    def _find_swap_recurse_swap(self, func_def: ast.FunctionDef, func_name: str) -> bool:
        swaps = []
        for child in ast.walk(func_def):
            if isinstance(child, ast.Assign):
                if len(child.targets) >= 1 and len(child.targets) <= 2:
                    for target in child.targets:
                        if isinstance(target, ast.Tuple) or isinstance(target, ast.List):
                            for elt in target.elts:
                                if isinstance(elt, ast.Subscript):
                                    swaps.append(child)
                        if isinstance(target, ast.Subscript):
                            swaps.append(child)
        has_swap_before = False
        has_swap_after = False
        for child in ast.walk(func_def):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == func_name:
                    for sibling in ast.walk(func_def):
                        if isinstance(sibling, ast.Assign) and sibling is not child:
                            for target in sibling.targets if hasattr(sibling, 'targets') else []:
                                if isinstance(target, (ast.Tuple, ast.List)):
                                    for elt in target.elts:
                                        if isinstance(elt, ast.Subscript):
                                            has_swap_before = True
                                if isinstance(target, ast.Subscript):
                                    has_swap_before = True
        for child in ast.walk(func_def):
            if isinstance(child, ast.For):
                if isinstance(child.iter, ast.Call):
                    if isinstance(child.iter.func, ast.Name) and child.iter.func.id == "range":
                        for stmt in child.body:
                            if isinstance(stmt, ast.Assign):
                                if len(stmt.targets) == 1 and isinstance(stmt.targets[0], (ast.Tuple, ast.List)):
                                    for elt in stmt.targets[0].elts:
                                        if isinstance(elt, ast.Subscript):
                                            return True
        return False

    def _find_visited_array(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        name = target.id.lower()
                        if any(kw in name for kw in ("used", "visited", "seen", "taken", "chosen", "cols")):
                            val = child.value
                            if isinstance(val, ast.List):
                                for elt in val.elts:
                                    if isinstance(elt, ast.Constant) and elt.value is False:
                                        return True
                            if isinstance(val, ast.ListComp):
                                return True
                            if isinstance(val, ast.BinOp) and isinstance(val.op, ast.Mult):
                                if isinstance(val.left, ast.List):
                                    for elt in val.left.elts:
                                        if isinstance(elt, ast.Constant) and elt.value is False:
                                            return True
            if isinstance(child, ast.Subscript):
                if isinstance(child.value, ast.Name):
                    name = child.value.id.lower()
                    if any(kw in name for kw in ("used", "visited", "seen", "taken", "cols")):
                        return True
        return False

    def _find_permutation_generation(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute) and child.func.attr == "append":
                    if isinstance(child.func.value, ast.Name):
                        name = child.func.value.id.lower()
                        if any(kw in name for kw in ("perm", "res", "result", "path", "sol", "curr")):
                            return True
        return False

    def _find_recursive_exploration(self, func_def: ast.FunctionDef, func_name: str) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == func_name:
                    for arg in child.args:
                        if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                            if isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                                return True
                            if isinstance(arg.left, ast.Constant) and arg.left.value == 1:
                                return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
