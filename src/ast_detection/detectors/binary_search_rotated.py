"""Detector for binary search in a rotated sorted array.

Detects the rotated array search pattern where a sorted array has been
rotated at an unknown pivot. The key distinction from standard binary
search is the sorted-half comparison (nums[left] <= nums[mid]) and the
target-range check in the sorted half.

Does NOT detect:
- Standard (non-rotated) binary search (no sorted-half comparison)
- Answer-space binary search (feasibility function call)
- Find-minimum in rotated array (no target range check)
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class BinarySearchRotatedDetector(BaseDetector):
    pattern_id = "binary_search_rotated"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_rotated_bs(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_sorted_half = any(e.type == "sorted_half_comparison" for e in evidence)
        has_target_range = any(e.type == "target_range_check" for e in evidence)

        detected = has_sorted_half and has_target_range

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_rotated_bs(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.While):
                continue

            if not self._is_binary_search_condition(node.test):
                continue

            has_midpoint = self._find_midpoint_calculation(node.body)
            if not has_midpoint:
                continue

            has_sorted_half = self._find_sorted_half_comparison(node.body)
            has_target_range = self._find_target_range_check(node.body)
            has_boundary_update = self._find_boundary_update(node.body)
            has_answer_space_check = self._find_answer_space_check(node.body)

            if has_answer_space_check:
                continue

            if has_midpoint:
                evidence.append(
                    EvidenceItem(
                        type="rotated_midpoint",
                        description="Midpoint calculation in rotated binary search",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
                    )
                )

            if has_sorted_half:
                evidence.append(
                    EvidenceItem(
                        type="sorted_half_comparison",
                        description="Sorted-half comparison: nums[left] <= nums[mid] or nums[mid] <= nums[right]",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.35,
                    )
                )

            if has_target_range:
                evidence.append(
                    EvidenceItem(
                        type="target_range_check",
                        description="Target-in-sorted-half range check",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

            if has_boundary_update:
                evidence.append(
                    EvidenceItem(
                        type="rotated_boundary_update",
                        description="Boundary update based on sorted-half logic",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

    def _is_binary_search_condition(self, test: ast.AST) -> bool:
        if not isinstance(test, ast.Compare):
            return False
        if len(test.ops) != 1:
            return False
        if not isinstance(test.ops[0], (ast.LtE, ast.Lt, ast.GtE, ast.Gt)):
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

    def _find_sorted_half_comparison(self, body: list) -> bool:
        for stmt in ast.walk(ast.Module(body=body)):
            if isinstance(stmt, ast.If):
                test = stmt.test
                if isinstance(test, ast.Compare) and len(test.ops) == 1:
                    if isinstance(test.ops[0], (ast.LtE, ast.Lt, ast.GtE, ast.Gt)):
                        left = test.left
                        right = test.comparators[0]
                        if isinstance(left, ast.Subscript) and isinstance(right, ast.Subscript):
                            if self._is_nums_subscript(left) and self._is_nums_subscript(right):
                                left_index = self._get_subscript_name(left)
                                right_index = self._get_subscript_name(right)
                                if left_index and right_index:
                                    if left_index in ("left", "low", "l", "lo", "mid", "m") and right_index in ("mid", "m", "right", "high", "r", "hi"):
                                        return True
                                if self._is_mid_or_boundary(left) and self._is_mid_or_boundary(right):
                                    return True
                            if self._is_nums_subscript(left) and isinstance(right, ast.Name):
                                return False
                if isinstance(test, ast.BoolOp):
                    for value in test.values:
                        if isinstance(value, ast.Compare) and len(value.ops) == 1:
                            if isinstance(value.ops[0], (ast.LtE, ast.Lt, ast.GtE, ast.Gt)):
                                left = value.left
                                right = value.comparators[0]
                                if isinstance(left, ast.Subscript) and isinstance(right, ast.Subscript):
                                    if self._is_nums_subscript(left) and self._is_nums_subscript(right):
                                        if self._is_mid_or_boundary(left) and self._is_mid_or_boundary(right):
                                            return True
        return False

    def _find_target_range_check(self, body: list) -> bool:
        for stmt in ast.walk(ast.Module(body=body)):
            if isinstance(stmt, ast.If):
                test = stmt.test
                comparisons = []
                if isinstance(test, ast.Compare):
                    comparisons = [test]
                elif isinstance(test, ast.BoolOp):
                    comparisons = [v for v in test.values if isinstance(v, ast.Compare)]

                for comp in comparisons:
                    if len(comp.ops) == 1:
                        left = comp.left
                        right = comp.comparators[0]
                        if isinstance(left, ast.Subscript) and isinstance(right, ast.Subscript):
                            if self._is_nums_subscript(left) and self._is_nums_subscript(right):
                                if self._is_target_ref(left) or self._is_target_ref(right):
                                    return True
                        if isinstance(left, ast.Subscript) and isinstance(right, ast.Name):
                            if self._is_nums_subscript(left):
                                target_name = right.id.lower()
                                if "target" in target_name or "t" == target_name or "key" in target_name:
                                    return True
                        if isinstance(left, ast.Name) and isinstance(right, ast.Subscript):
                            if self._is_nums_subscript(right):
                                target_name = left.id.lower()
                                if "target" in target_name or "t" == target_name or "key" in target_name:
                                    return True

                    if len(comp.ops) == 2 and isinstance(comp.ops[0], (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                        if isinstance(comp.left, ast.Name):
                            target_name = comp.left.id.lower()
                            if "target" in target_name or "t" == target_name or "key" in target_name:
                                return True
                        if isinstance(comp.comparators[1], ast.Name):
                            target_name = comp.comparators[1].id.lower()
                            if "target" in target_name or "t" == target_name or "key" in target_name:
                                return True
                        if isinstance(comp.comparators[0], ast.Name):
                            target_name = comp.comparators[0].id.lower()
                            if "target" in target_name or "t" == target_name or "key" in target_name:
                                return True
        return False

    def _is_nums_subscript(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name):
                name = node.value.id.lower()
                return any(kw in name for kw in ("nums", "arr", "a", "array", "list", "values"))
        return False

    def _get_subscript_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Subscript):
            if isinstance(node.slice, ast.Name):
                return node.slice.id.lower()
            if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                return node.slice.value.lower()
        return None

    def _is_mid_or_boundary(self, node: ast.AST) -> bool:
        name = self._get_subscript_name(node)
        if name:
            return name in ("left", "low", "l", "lo", "mid", "m", "right", "high", "r", "hi")
        return False

    def _is_target_ref(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Subscript):
            name = self._get_subscript_name(node)
            if name:
                return "target" in name or "t" == name or "key" in name
        return False

    def _find_boundary_update(self, body: list) -> bool:
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

    def _find_answer_space_check(self, body: list) -> bool:
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
