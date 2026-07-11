"""Detector for greedy interval scheduling/merging pattern.

Detects interval-based greedy algorithms such as interval scheduling
(maximum non-overlapping intervals), interval merging, and minimum
arrows to burst balloons.

Does NOT detect:
- Ordinary sorting without interval operations
- Non-interval greedy algorithms
- Dynamic programming on intervals
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class GreedyIntervalDetector(BaseDetector):
    pattern_id = "greedy_interval"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_greedy_interval(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_interval_sorting = any(e.type == "interval_sorting" for e in evidence)
        has_interval_comparison = any(e.type == "interval_comparison" for e in evidence)
        has_merge_scheduling = any(e.type == "interval_merge_scheduling" for e in evidence)

        detected = has_interval_sorting and (has_interval_comparison or has_merge_scheduling)

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_greedy_interval(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.FunctionDef):
                continue

            has_sorting = self._find_interval_sorting(node)
            has_comparison = self._find_interval_comparison(node)
            has_merge = self._find_interval_merge_scheduling(node)
            has_selection = self._find_greedy_selection(node)

            if not has_sorting:
                continue

            if has_sorting:
                evidence.append(
                    EvidenceItem(
                        type="interval_sorting",
                        description="Sorting intervals by start or end value",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

            if has_comparison:
                evidence.append(
                    EvidenceItem(
                        type="interval_comparison",
                        description="Comparing interval start/end values in conditionals",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

            if has_merge:
                evidence.append(
                    EvidenceItem(
                        type="interval_merge_scheduling",
                        description="Interval merge or scheduling operation",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

            if has_selection:
                evidence.append(
                    EvidenceItem(
                        type="greedy_selection",
                        description="Greedy selection of intervals",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

    def _find_tuple_unpacked_interval_vars(self, func_def: ast.FunctionDef) -> set:
        """Find variable names created by tuple unpacking in for-loop targets.

        Tracks ``for x, y in iterable:`` patterns where the loop target is a
        Tuple of Name nodes.  Both the first-element and second-element names
        are returned (they represent interval start/end values after sorting).
        """
        unpacked: set = set()
        for child in ast.walk(func_def):
            if isinstance(child, ast.For) and isinstance(child.target, ast.Tuple):
                for elt in child.target.elts:
                    if isinstance(elt, ast.Name):
                        unpacked.add(elt.id)
        return unpacked

    def _find_interval_sorting(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == "sorted":
                    for kw in child.keywords:
                        if kw.arg == "key" and isinstance(kw.value, ast.Lambda):
                            if self._lambda_accesses_interval(kw.value):
                                return True
                if isinstance(child.func, ast.Attribute) and child.func.attr == "sort":
                    for kw in child.keywords:
                        if kw.arg == "key" and isinstance(kw.value, ast.Lambda):
                            if self._lambda_accesses_interval(kw.value):
                                return True
        return False

    def _lambda_accesses_interval(self, lambda_node: ast.Lambda) -> bool:
        for child in ast.walk(lambda_node):
            if isinstance(child, ast.Subscript):
                if isinstance(child.slice, ast.Constant) and child.slice.value in (0, 1):
                    return True
            if isinstance(child, ast.Attribute):
                if child.attr in ("start", "end", "left", "right"):
                    return True
        return False

    def _compare_involves_tracked(
        self, compare_node: ast.Compare, tracked: set
    ) -> bool:
        """Return True if either side of *compare_node* is a tracked Name."""
        for side in (compare_node.left, compare_node.comparators[0]):
            if isinstance(side, ast.Name) and side.id in tracked:
                return True
        return False

    def _find_interval_comparison(self, func_def: ast.FunctionDef) -> bool:
        tracked = self._find_tuple_unpacked_interval_vars(func_def)
        for child in ast.walk(func_def):
            if isinstance(child, ast.Compare):
                for side in (child.left, child.comparators[0]):
                    if isinstance(side, ast.Subscript):
                        if isinstance(side.value, ast.Name):
                            name = side.value.id.lower()
                            if "interval" in name or "intervals" in name or "balloon" in name or "point" in name:
                                return True
                    if isinstance(side, ast.Attribute):
                        if side.attr in ("start", "end", "left", "right"):
                            return True
                if isinstance(child.ops[0], (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                    for side in (child.left, child.comparators[0]):
                        if isinstance(side, ast.Subscript):
                            if isinstance(side.slice, ast.Constant) and side.slice.value in (0, 1):
                                return True
                if tracked and self._compare_involves_tracked(child, tracked):
                    return True
            if isinstance(child, ast.If):
                if isinstance(child.test, ast.Compare):
                    for side in (child.test.left, child.test.comparators[0]):
                        if isinstance(side, ast.Subscript):
                            if isinstance(side.slice, ast.Constant) and side.slice.value in (0, 1):
                                return True
                    if tracked and self._compare_involves_tracked(child.test, tracked):
                        return True
        return False

    def _find_interval_merge_scheduling(self, func_def: ast.FunctionDef) -> bool:
        tracked = self._find_tuple_unpacked_interval_vars(func_def)
        for child in ast.walk(func_def):
            if isinstance(child, ast.If):
                has_interval_compare = self._has_interval_subscript_compare(child.test)
                if not has_interval_compare and tracked:
                    has_interval_compare = self._has_interval_compare_with_tracked(child.test, tracked)
                if not has_interval_compare:
                    continue
                bodies = list(child.body) + list(child.orelse)
                for stmt in bodies:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Subscript):
                                if isinstance(target.slice, ast.Constant) and target.slice.value in (0, 1):
                                    return True
                            if isinstance(target, ast.Attribute):
                                if target.attr in ("end", "start", "left", "right"):
                                    return True
                                if isinstance(target.value, ast.Name):
                                    name = target.value.id.lower()
                                    if "merged" in name or "result" in name or "new" in name:
                                        return True
        return False

    def _has_interval_subscript_compare(self, test_node: ast.AST) -> bool:
        for sub in ast.walk(test_node):
            if isinstance(sub, ast.Compare):
                if len(sub.ops) == 1 and isinstance(sub.ops[0], (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                    for side in (sub.left, sub.comparators[0]):
                        if isinstance(side, ast.Subscript):
                            if isinstance(side.slice, ast.Constant) and side.slice.value in (0, 1):
                                return True
        return False

    def _has_interval_compare_with_tracked(
        self, test_node: ast.AST, tracked: set
    ) -> bool:
        """Like _has_interval_subscript_compare but also accepts tracked Names."""
        for sub in ast.walk(test_node):
            if isinstance(sub, ast.Compare):
                if len(sub.ops) == 1 and isinstance(sub.ops[0], (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                    if self._compare_involves_tracked(sub, tracked):
                        return True
        return False

    def _find_greedy_selection(self, func_def: ast.FunctionDef) -> bool:
        tracked = self._find_tuple_unpacked_interval_vars(func_def)
        for child in ast.walk(func_def):
            if isinstance(child, ast.If):
                if isinstance(child.test, ast.Compare):
                    has_subscript_gate = False
                    for side in (child.test.left, child.test.comparators[0]):
                        if isinstance(side, ast.Subscript):
                            if isinstance(side.slice, ast.Constant) and side.slice.value in (0, 1):
                                has_subscript_gate = True
                                break
                    if not has_subscript_gate and tracked:
                        has_subscript_gate = self._compare_involves_tracked(child.test, tracked)
                    if has_subscript_gate:
                        for stmt in child.body:
                            if isinstance(stmt, ast.AugAssign):
                                if isinstance(stmt.target, ast.Name):
                                    target = stmt.target.id.lower()
                                    if any(kw in target for kw in ("count", "res", "cnt", "total")):
                                        return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
