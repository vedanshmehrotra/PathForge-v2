"""Detector for interval DP pattern.

Detects structural evidence of interval dynamic programming where a 2D
table is filled over subarray/substring intervals of increasing length.
Characteristic of Matrix Chain Multiplication, Palindrome Partitioning II,
Burst Balloons, Longest Palindromic Subsequence, and Stone Game.

Length-based loop is the primary structural signal for interval DP.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class DPIntervalDetector(BaseDetector):
    pattern_id = "dp_interval"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_interval(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_length_loop = any(e.type == "length_based_loop" for e in evidence)
        has_array = any(e.type == "dp_array_2d" for e in evidence)
        has_pair = any(e.type == "pair_loop" for e in evidence)
        has_lookback = any(e.type == "grid_lookback" for e in evidence)
        has_recurrence = any(e.type == "recurrence_expression" for e in evidence)
        has_string = any(e.type == "string_compare" for e in evidence)

        supporting_count = sum([has_array, has_pair, has_lookback, has_recurrence])
        detected = has_length_loop and supporting_count >= 2 and not has_string

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_interval(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if isinstance(node, ast.FunctionDef):
                has_length = self._find_length_based_loop(node)
                has_array = self._find_dp_array_2d(node)
                has_pair = self._find_pair_loop(node)
                has_lookback = self._find_grid_lookback(node)
                has_recurrence = self._find_recurrence_expression(node)
                has_aggregation = self._find_result_aggregation(node)
                has_string = self._find_string_compare(node)
                has_partition_lookback = self._find_partition_lookback(node)

                if has_length:
                    evidence.append(
                        EvidenceItem(
                            type="length_based_loop",
                            description="Length-based outer loop over interval/gap size — primary interval DP signal",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.35,
                        )
                    )

                if has_array:
                    evidence.append(
                        EvidenceItem(
                            type="dp_array_2d",
                            description="2D DP array for interval table",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )

                if has_pair:
                    evidence.append(
                        EvidenceItem(
                            type="pair_loop",
                            description="Pair loop i..j interval pair inside length-based iteration",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )

                if has_lookback:
                    evidence.append(
                        EvidenceItem(
                            type="grid_lookback",
                            description="Grid lookback with partition dp[i][k] + dp[k+1][j]",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )

                if has_recurrence:
                    evidence.append(
                        EvidenceItem(
                            type="recurrence_expression",
                            description="Interval recurrence with max/min over partition points",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )

                if has_partition_lookback:
                    evidence.append(
                        EvidenceItem(
                            type="partition_lookback",
                            description="Partition lookback dp[i][k] + dp[k+1][j] pattern",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.20,
                        )
                    )

                if has_aggregation:
                    evidence.append(
                        EvidenceItem(
                            type="result_aggregation",
                            description="Result aggregation returning dp[0][n-1]",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.15,
                        )
                    )

    def _find_length_based_loop(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.For):
                if isinstance(node.iter, ast.Call):
                    if isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                        target = node.target.id.lower()
                        if target in ("length", "len", "l", "gap", "g"):
                            return True
                        if len(node.iter.args) >= 2:
                            return True
        return False

    def _find_dp_array_2d(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.ListComp):
                    for generator in node.value.generators:
                        if isinstance(generator.iter, ast.Call):
                            if isinstance(generator.iter.func, ast.Name) and generator.iter.func.id == "range":
                                inner = node.value.elt
                                if isinstance(inner, (ast.List, ast.BinOp)):
                                    return True
        return False

    def _find_pair_loop(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.For):
                if self._is_length_loop(node):
                    for child in ast.walk(node):
                        if isinstance(child, ast.For) and child is not node:
                            for sub in ast.walk(child):
                                if isinstance(sub, ast.Assign):
                                    for target in sub.targets:
                                        if isinstance(target, ast.Name):
                                            name = target.id.lower()
                                            if name in ("j", "end", "right"):
                                                val = sub.value
                                                if isinstance(val, ast.BinOp):
                                                    names_in_val = set()
                                                    for s in ast.walk(val):
                                                        if isinstance(s, ast.Name):
                                                            names_in_val.add(s.id.lower())
                                                    if any(n in ("i", "start", "idx", "left") for n in names_in_val):
                                                        return True
                                                    if node.target.id.lower() in names_in_val:
                                                        return True
        return False

    def _is_length_loop(self, loop_node: ast.For) -> bool:
        if isinstance(loop_node.iter, ast.Call):
            if isinstance(loop_node.iter.func, ast.Name) and loop_node.iter.func.id == "range":
                target = loop_node.target.id.lower()
                if target in ("length", "len", "l", "gap", "g"):
                    return True
                if len(loop_node.iter.args) >= 2:
                    return True
        return False

    def _find_grid_lookback(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Subscript):
                    if isinstance(node.value.value, ast.Name) and node.value.value.id.lower().startswith("dp"):
                        return True
        return False

    def _find_recurrence_expression(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("max", "min"):
                    for arg in node.args:
                        if self._has_dp_reference(arg):
                            for stmt in ast.walk(func_def):
                                if isinstance(stmt, ast.Assign):
                                    for target in stmt.targets:
                                        if self._has_dp_reference(target):
                                            return True
        return False

    def _has_dp_reference(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name) and node.value.id.lower().startswith("dp"):
                return True
            if isinstance(node.value, ast.Subscript):
                if isinstance(node.value.value, ast.Name) and node.value.value.id.lower().startswith("dp"):
                    return True
        if isinstance(node, ast.BinOp):
            return self._has_dp_reference(node.left) or self._has_dp_reference(node.right)
        if isinstance(node, ast.Call):
            for arg in node.args:
                if self._has_dp_reference(arg):
                    return True
        return False

    def _find_partition_lookback(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                has_left = False
                has_right = False
                for sub in ast.walk(node.left):
                    if isinstance(sub, ast.Subscript):
                        if isinstance(sub.value, ast.Subscript):
                            if isinstance(sub.value.value, ast.Name) and sub.value.value.id.lower().startswith("dp"):
                                has_left = True
                for sub in ast.walk(node.right):
                    if isinstance(sub, ast.Subscript):
                        if isinstance(sub.value, ast.Subscript):
                            if isinstance(sub.value.value, ast.Name) and sub.value.value.id.lower().startswith("dp"):
                                has_right = True
                if has_left and has_right:
                    return True
        return False

    def _find_result_aggregation(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Return):
                if isinstance(node.value, ast.Subscript):
                    cur = node.value
                    while isinstance(cur, ast.Subscript):
                        if isinstance(cur.value, ast.Name) and cur.value.id.lower().startswith("dp"):
                            return True
                        cur = cur.value
        return False

    def _find_string_compare(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Compare):
                for op in node.ops:
                    if isinstance(op, ast.Eq):
                        for side in [node.left] + node.comparators:
                            if isinstance(side, ast.Subscript):
                                if isinstance(side.value, ast.Name):
                                    name = side.value.id.lower()
                                    if name in ("s", "str", "word", "text", "char", "a", "b", "p", "q", "t"):
                                        return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
