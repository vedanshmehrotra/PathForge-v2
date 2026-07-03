"""Detector for brute_force diagnostic pattern.

Detects obvious exhaustive-search structures without judging optimality.
Requires strong evidence: nested loops, pair-wise checking, or recursive
branching enumeration.

This detector NEVER fires based on absence of other detectors.
It ONLY fires on explicit structural evidence of exhaustive search.
A single flat loop does NOT trigger this detector.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class BruteForceDetector(BaseDetector):
    pattern_id = "brute_force"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        has_nested = self._detect_nested_loops(ast_root, evidence)
        has_range = self._detect_range_enumeration(ast_root, evidence)
        has_pair = self._detect_pair_checking(ast_root, evidence)
        has_branch = self._detect_recursive_branching(ast_root, evidence)

        has_exhaustive_core = has_nested or has_branch
        confidence = self._calculate_confidence(evidence, has_exhaustive_core)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence if has_exhaustive_core else [],
            detected=confidence > 0.0,
        )

    def _detect_nested_loops(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in ast.walk(ast_root):
            if isinstance(node, (ast.For, ast.While)):
                body_is_loop = any(
                    isinstance(stmt, (ast.For, ast.While))
                    for stmt in node.body
                )
                if body_is_loop:
                    evidence.append(
                        EvidenceItem(
                            type="nested_loops",
                            description="Nested loop structure indicating exhaustive iteration",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                            weight=0.35,
                        )
                    )
                    found = True
        return found

    def _detect_range_enumeration(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in ast.walk(ast_root):
            if isinstance(node, ast.For):
                if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name):
                    if node.iter.func.id == "range":
                        evidence.append(
                            EvidenceItem(
                                type="range_enumeration",
                                description=f"Range-based exhaustive iteration: {ast.unparse(node.iter)}",
                                location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                                weight=0.20,
                            )
                        )
                        found = True
        return found

    def _detect_pair_checking(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in ast.walk(ast_root):
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Compare):
                    has_subscript = any(
                        isinstance(c, ast.Subscript)
                        for c in [node.test.left] + node.test.comparators
                    )
                    if has_subscript:
                        evidence.append(
                            EvidenceItem(
                                type="pair_wise_check",
                                description=f"Element comparison: {ast.unparse(node.test)}",
                                location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                                weight=0.25,
                            )
                        )
                        found = True
        return found

    def _detect_recursive_branching(self, ast_root: ast.AST, evidence: list) -> bool:
        found = False
        for node in ast.walk(ast_root):
            if isinstance(node, ast.FunctionDef):
                recursive_calls = sum(
                    1 for child in ast.walk(node)
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
                    and child.func.id == node.name
                )
                if recursive_calls >= 2:
                    evidence.append(
                        EvidenceItem(
                            type="recursive_branching",
                            description=f"Function '{node.name}' has {recursive_calls} recursive calls indicating exhaustive branching",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                            weight=0.20,
                        )
                    )
                    found = True
                elif recursive_calls >= 1:
                    has_loop_in_body = any(
                        isinstance(stmt, (ast.For, ast.While))
                        for stmt in node.body
                    )
                    has_loop_nested = any(
                        isinstance(stmt, (ast.For, ast.While))
                        for stmt in ast.walk(node)
                    )
                    if has_loop_in_body or has_loop_nested:
                        evidence.append(
                            EvidenceItem(
                                type="recursive_branching",
                                description=f"Function '{node.name}' has recursion with loop-based branching",
                                location=f"{node.lineno}:{node.col_offset}" if hasattr(node, 'lineno') else None,
                                weight=0.25,
                            )
                        )
                        found = True
        return found

    def _calculate_confidence(self, evidence: list, has_core: bool) -> float:
        if not evidence or not has_core:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
