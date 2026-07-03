"""Detector for answer-space binary search.

Detects binary search over the answer domain (feasibility-check based) rather
than over array indices. Characterized by low/high boundaries, a check(mid)
feasibility function call, and single-sided narrowing.

Does NOT detect classic (index-based) binary search.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class BinarySearchAnswerDetector(BaseDetector):
    pattern_id = "binary_search_answer"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_answer_space_bs(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=confidence > 0.0,
        )

    def _detect_answer_space_bs(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: while loop with answer-space binary search pattern.

        Core pattern:
            low, high = 0, max_val
            while low < high:
                mid = (low + high) // 2
                if is_feasible(mid):
                    high = mid
                else:
                    low = mid + 1
            return low
        """
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.While):
                continue

            if not self._is_binary_search_condition(node.test):
                continue

            has_midpoint = self._find_midpoint_calculation(node.body)
            has_feasibility_check = self._find_feasibility_check(node.body)
            has_boundary_update = self._find_boundary_update(node.body)

            if has_midpoint and has_feasibility_check:
                if has_midpoint:
                    evidence.append(
                        EvidenceItem(
                            type="answer_midpoint",
                            description="Midpoint calculation in answer space",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.30,
                        )
                    )
                if has_feasibility_check:
                    evidence.append(
                        EvidenceItem(
                            type="feasibility_check",
                            description=f"Feasibility check on mid value",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.40,
                        )
                    )
                if has_boundary_update:
                    evidence.append(
                        EvidenceItem(
                            type="answer_boundary_update",
                            description="Boundary update based on feasibility: high = mid or low = mid + 1",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )
                evidence.append(
                    EvidenceItem(
                        type="feasibility_loop",
                        description="Answer-space binary search while loop",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
                    )
                )

    def _is_binary_search_condition(self, test: ast.AST) -> bool:
        """Check if the while condition is a binary search pattern (low < high or low <= high)."""
        if not isinstance(test, ast.Compare):
            return False
        if len(test.ops) != 1:
            return False
        if not isinstance(test.ops[0], (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
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
        """Check if the loop body contains a midpoint calculation."""
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
                            if isinstance(val.left, ast.Name) and isinstance(val.right, ast.Name):
                                return True
        return False

    def _find_feasibility_check(self, body: list) -> bool:
        """Check if there's a feasibility function call with mid as argument.

        Matches: if is_feasible(mid): or if check(mid) or if can_place(mid)
        The key signal is a function call with mid as the argument used as an
        If condition (not a comparison arr[mid] == target, which is classic BS).
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
                if isinstance(test, ast.BoolOp):
                    for value_node in test.values:
                        if isinstance(value_node, ast.Call):
                            for arg in value_node.args:
                                if isinstance(arg, ast.Name) and arg.id in ("mid", "m", "middle", "pivot"):
                                    return True
        return False

    def _find_boundary_update(self, body: list) -> bool:
        """Check for boundary updates characteristic of answer-space BS.

        Key distinction from classic: answer-space does high = mid (not mid-1)
        and low = mid + 1. The single-sided narrowing (high = mid) is distinctive.
        """
        has_narrowing = False
        for stmt in ast.walk(ast.Module(body=body)):
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id in ("left", "low", "l", "lo", "right", "high", "r", "hi"):
                        val = stmt.value
                        if isinstance(val, ast.Name) and val.id in ("mid", "m", "middle", "pivot"):
                            has_narrowing = True
                        if isinstance(val, ast.BinOp):
                            if isinstance(val.right, ast.Constant) and val.right.value == 1:
                                if isinstance(val.left, ast.Name) and val.left.id in ("mid", "m", "middle", "pivot"):
                                    has_narrowing = True
        return has_narrowing

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
