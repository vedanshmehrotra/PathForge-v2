"""Detector for 2D string DP pattern.

Detects structural evidence of 2D string dynamic programming where a
table is filled based on character comparison between two strings.
Characteristic of Edit Distance (Levenshtein), Longest Common Subsequence
(LCS), Wildcard Matching, Regular Expression Matching, and Distinct
Subsequences.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class DP2DStringDetector(BaseDetector):
    pattern_id = "dp_2d_string"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_2d_string(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_string_compare = any(e.type == "string_compare" for e in evidence)
        has_grid_lookback = any(e.type == "grid_lookback" for e in evidence)
        has_array = any(e.type == "dp_array_2d" for e in evidence)
        has_nested = any(e.type == "nested_fill_loops" for e in evidence)
        has_recurrence = any(e.type == "recurrence_expression" for e in evidence)
        has_base = any(e.type == "base_case_return" for e in evidence)

        secondary_count = sum([has_array, has_nested, has_recurrence, has_base])
        detected = has_string_compare and has_grid_lookback and secondary_count >= 1

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_2d_string(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if isinstance(node, ast.FunctionDef):
                has_string = self._find_string_compare(node)
                has_grid_lb = self._find_grid_lookback(node)
                has_array = self._find_dp_array_2d(node)
                has_nested = self._find_nested_fill_loops(node)
                has_recurrence = self._find_recurrence_expression(node)
                has_base = self._find_base_case(node)
                has_aggregation = self._find_result_aggregation(node)

                if has_string:
                    evidence.append(
                        EvidenceItem(
                            type="string_compare",
                            description="String character comparison in nested loops",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.30,
                        )
                    )

                if has_grid_lb:
                    evidence.append(
                        EvidenceItem(
                            type="grid_lookback",
                            description="Grid lookback dp[i-1][j-1], dp[i-1][j] in recurrence",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )

                if has_array:
                    evidence.append(
                        EvidenceItem(
                            type="dp_array_2d",
                            description="2D DP array for string alignment",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )

                if has_nested:
                    evidence.append(
                        EvidenceItem(
                            type="nested_fill_loops",
                            description="Two-level nested loop over string indices",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.20,
                        )
                    )

                if has_recurrence:
                    evidence.append(
                        EvidenceItem(
                            type="recurrence_expression",
                            description="String DP recurrence with max/min combining lookback",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.20,
                        )
                    )

                if has_base:
                    evidence.append(
                        EvidenceItem(
                            type="base_case_return",
                            description="Base case initialization for string DP boundaries",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.15,
                        )
                    )

                if has_aggregation:
                    evidence.append(
                        EvidenceItem(
                            type="result_aggregation",
                            description="Result aggregation returning dp[m][n]",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.15,
                        )
                    )

    def _find_string_compare(self, func_def: ast.FunctionDef) -> bool:
        string_var_count = 0
        for node in ast.walk(func_def):
            if isinstance(node, ast.Compare):
                for op in node.ops:
                    if isinstance(op, ast.Eq):
                        for side in [node.left] + node.comparators:
                            if isinstance(side, ast.Subscript):
                                if isinstance(side.value, ast.Name):
                                    name = side.value.id.lower()
                                    if name.startswith(("s", "str", "word", "text", "char", "a", "b", "p", "q", "t")):
                                        string_var_count += 1
        return string_var_count >= 2

    def _find_grid_lookback(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Subscript):
                    if isinstance(node.value.value, ast.Name) and node.value.value.id.lower().startswith("dp"):
                        inner_slice = node.value.slice
                        outer_slice = node.slice
                        if isinstance(inner_slice, ast.BinOp) and isinstance(inner_slice.op, ast.Sub):
                            return True
                        if isinstance(outer_slice, ast.BinOp) and isinstance(outer_slice.op, ast.Sub):
                            return True
        return False

    def _find_dp_array_2d(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.ListComp):
                    for generator in node.value.generators:
                        if isinstance(generator.iter, ast.Call):
                            if isinstance(generator.iter.func, ast.Name) and generator.iter.func.id == "range":
                                inner_list = node.value.elt
                                if isinstance(inner_list, ast.BinOp) and isinstance(inner_list.op, ast.Mult):
                                    return True
        return False

    def _find_nested_fill_loops(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.For):
                for child in ast.walk(node):
                    if isinstance(child, ast.For) and child is not node:
                        has_dp_write = self._has_dp_2d_write(child)
                        if has_dp_write:
                            return True
        return False

    def _has_dp_2d_write(self, loop_node: ast.For) -> bool:
        for node in ast.walk(loop_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Subscript):
                        if isinstance(target.value, ast.Subscript):
                            if isinstance(target.value.value, ast.Name) and target.value.value.id.lower().startswith("dp"):
                                return True
        return False

    def _find_recurrence_expression(self, func_def: ast.FunctionDef) -> bool:
        has_max_min = False
        for node in ast.walk(func_def):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("max", "min"):
                    has_max_min = True
                    for arg in node.args:
                        if isinstance(arg, ast.BinOp):
                            for sub in ast.walk(arg):
                                if isinstance(sub, ast.Subscript):
                                    if isinstance(sub.value, ast.Name) and sub.value.id.lower().startswith("dp"):
                                        return True
        return has_max_min

    def _find_base_case(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Compare):
                    for side in [node.test.left] + node.test.comparators:
                        if isinstance(side, ast.Name) and side.id.lower() in ("i", "j", "m", "n", "row", "col"):
                            for stmt in node.body:
                                if isinstance(stmt, ast.Assign):
                                    return True
        return False

    def _find_result_aggregation(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Return):
                if isinstance(node.value, ast.Subscript):
                    if isinstance(node.value.value, ast.Subscript):
                        if isinstance(node.value.value.value, ast.Name) and node.value.value.value.id.lower().startswith("dp"):
                            return True
                    if isinstance(node.value.value, ast.Name) and node.value.value.id.lower().startswith("dp"):
                        if isinstance(node.value.slice, ast.UnaryOp):
                            return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
