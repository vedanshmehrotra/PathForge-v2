"""Detector for classic binary search over an ordered search space (array indices).

Detects the textbook binary search pattern: while left <= right loop with
midpoint calculation and boundary updates based on element comparison.

Does NOT detect answer-space binary search (feasibility-check based).
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class BinarySearchClassicDetector(BaseDetector):
    pattern_id = "binary_search_standard"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_binary_search_while(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=confidence > 0.0,
        )

    def _detect_binary_search_while(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: while loop with binary search structure.

        Core pattern:
            left, right = 0, len(arr) - 1
            while left <= right:
                mid = (left + right) // 2
                if arr[mid] == target:
                    return mid
                elif arr[mid] < target:
                    left = mid + 1
                else:
                    right = mid - 1
        """
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.While):
                continue

            if not self._is_binary_search_condition(node.test):
                continue

            has_midpoint = self._find_midpoint_calculation(node.body)
            has_boundary_update = self._find_boundary_update(node.body)
            has_mid_comparison = self._find_mid_comparison(node.body)
            has_answer_space_check = self._find_answer_space_check(node.body)

            if has_midpoint and has_boundary_update and not has_answer_space_check:
                if has_midpoint:
                    evidence.append(
                        EvidenceItem(
                            type="binary_midpoint",
                            description="Midpoint calculation: (left + right) // 2",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.35,
                        )
                    )
                if has_boundary_update:
                    evidence.append(
                        EvidenceItem(
                            type="boundary_update",
                            description="Boundary update: left = mid + 1 or right = mid - 1",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )
                if has_mid_comparison:
                    evidence.append(
                        EvidenceItem(
                            type="mid_comparison",
                            description="Element comparison at mid index",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.30,
                        )
                    )
                evidence.append(
                    EvidenceItem(
                        type="left_right_boundary",
                        description="Binary search while loop with left/right boundaries",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
                    )
                )

    def _is_binary_search_condition(self, test: ast.AST) -> bool:
        """Check if the while condition is a binary search pattern (left <= right or left < right)."""
        if not isinstance(test, ast.Compare):
            return False
        if len(test.ops) != 1:
            return False
        if not isinstance(test.ops[0], (ast.LtE, ast.Lt, ast.LtE, ast.GtE, ast.Gt)):
            return False
        if isinstance(test.left, ast.Name) and isinstance(test.comparators[0], ast.Name):
            left_id = test.left.id
            right_id = test.comparators[0].id
            if left_id in ("left", "low", "l", "lo", "start", "i") and right_id in ("right", "high", "r", "hi", "end", "j"):
                return True
            if left_id in ("right", "high", "r", "hi", "end", "j") and right_id in ("left", "low", "l", "lo", "start", "i"):
                return True
        return False

    def _find_midpoint_calculation(self, body: list) -> bool:
        """Check if the loop body contains a midpoint calculation.

        Matches: mid = (left + right) // 2  or  mid = left + (right - left) // 2
        """
        for stmt in ast.walk(ast.Module(body=body)):
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id in ("mid", "m", "middle", "pivot"):
                        val = stmt.value
                        if isinstance(val, ast.BinOp) and isinstance(val.op, ast.FloorDiv):
                            if isinstance(val.left, ast.BinOp) and isinstance(val.left.op, ast.Add):
                                return True
                            if isinstance(val.left, ast.BinOp) and isinstance(val.left.op, ast.Sub):
                                return True
                            if isinstance(val.left, ast.Name):
                                return True
                        if isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add):
                            if isinstance(val.left, ast.BinOp) and isinstance(val.left.op, ast.FloorDiv):
                                return True
                            if isinstance(val.left, ast.Name):
                                if isinstance(val.right, ast.BinOp) and isinstance(val.right.op, ast.FloorDiv):
                                    return True
                        if isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add):
                            if isinstance(val.left, ast.Name) and isinstance(val.right, ast.Name):
                                return True
        return False

    def _find_boundary_update(self, body: list) -> bool:
        """Check if the loop body contains boundary updates.

        Matches: left = mid + 1  or  right = mid - 1
        """
        for stmt in ast.walk(ast.Module(body=body)):
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id in ("left", "low", "l", "lo", "right", "high", "r", "hi"):
                        val = stmt.value
                        if isinstance(val, ast.BinOp):
                            if isinstance(val.op, (ast.Add, ast.Sub)):
                                if isinstance(val.left, ast.Name) and val.left.id in ("mid", "m", "middle", "pivot"):
                                    return True
                                if isinstance(val.right, ast.Name) and val.right.id in ("mid", "m", "middle", "pivot"):
                                    return True
                                if isinstance(val.left, ast.Name) and val.left.id == target.id:
                                    if isinstance(val.right, ast.Constant) and isinstance(val.right.value, int):
                                        return True
        return False

    def _find_mid_comparison(self, body: list) -> bool:
        """Check if there's a comparison using the mid index to access array elements.

        Matches: if arr[mid] == target  or  elif arr[mid] < target
        """
        for stmt in ast.walk(ast.Module(body=body)):
            if isinstance(stmt, ast.If):
                test = stmt.test
                if isinstance(test, ast.Compare):
                    for sub in ast.walk(test):
                        if isinstance(sub, ast.Subscript):
                            if isinstance(sub.slice, ast.Name) and sub.slice.id in ("mid", "m", "middle", "pivot"):
                                return True
                            if isinstance(sub.value, ast.Name):
                                if isinstance(sub.slice, ast.Name):
                                    return True
        return False

    def _find_answer_space_check(self, body: list) -> bool:
        """Check if there's a feasibility function call (answer-space BS pattern).

        A function call with mid as argument in an if condition indicates
        answer-space binary search, not classic index-based binary search.
        """
        for stmt in ast.walk(ast.Module(body=body)):
            if isinstance(stmt, ast.If):
                test = stmt.test
                if isinstance(test, ast.Call):
                    for arg in test.args:
                        if isinstance(arg, ast.Name) and arg.id in ("mid", "m", "middle", "pivot"):
                            return True
                if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
                    if isinstance(test.operand, ast.Call):
                        for arg in test.operand.args:
                            if isinstance(arg, ast.Name) and arg.id in ("mid", "m", "middle", "pivot"):
                                return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
