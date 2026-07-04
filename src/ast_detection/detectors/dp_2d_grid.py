"""Detector for 2D grid DP pattern.

Detects structural evidence of 2D grid dynamic programming where a table
is filled row-by-row or column-by-column, with each cell depending on
neighbors above, left, or diagonal. Characteristic of Minimum Path Sum,
Unique Paths, Maximal Square, Dungeon Game.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class DP2DGridDetector(BaseDetector):
    pattern_id = "dp_2d_grid"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_2d_grid(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_grid_lookback = any(e.type == "grid_lookback" for e in evidence)
        has_nested_loops = any(e.type == "nested_fill_loops" for e in evidence)
        has_array = any(e.type == "dp_array_2d" for e in evidence)
        has_recurrence = any(e.type == "recurrence_expression" for e in evidence)
        has_aggregation = any(e.type == "result_aggregation" for e in evidence)
        has_string_compare = any(e.type == "string_compare" for e in evidence)

        secondary_count = sum([has_array, has_recurrence, has_aggregation])
        detected = has_grid_lookback and has_nested_loops and secondary_count >= 1

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_2d_grid(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if isinstance(node, ast.FunctionDef):
                has_grid_lb = self._find_grid_lookback(node)
                has_nested = self._find_nested_fill_loops(node)
                has_array = self._find_dp_array_2d(node)
                has_recurrence = self._find_recurrence_expression(node)
                has_aggregation = self._find_result_aggregation(node)
                has_base = self._find_base_case(node)
                has_string = self._find_string_compare(node)

                if has_grid_lb:
                    evidence.append(
                        EvidenceItem(
                            type="grid_lookback",
                            description="Grid lookback dp[r-1][c], dp[r][c-1] in recurrence",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.30,
                        )
                    )

                if has_nested:
                    evidence.append(
                        EvidenceItem(
                            type="nested_fill_loops",
                            description="Two-level nested loop over grid rows and columns",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.20,
                        )
                    )

                if has_array:
                    evidence.append(
                        EvidenceItem(
                            type="dp_array_2d",
                            description="2D DP array via nested list comprehension",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.30,
                        )
                    )

                if has_recurrence:
                    evidence.append(
                        EvidenceItem(
                            type="recurrence_expression",
                            description="Grid recurrence expression combining lookback terms",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.20,
                        )
                    )

                if has_aggregation:
                    evidence.append(
                        EvidenceItem(
                            type="result_aggregation",
                            description="Result aggregation returning dp[-1][-1] or corner cell",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.15,
                        )
                    )

                if has_base:
                    evidence.append(
                        EvidenceItem(
                            type="base_case_return",
                            description="Base case for grid boundary initialization",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.15,
                        )
                    )

                if has_string:
                    evidence.append(
                        EvidenceItem(
                            type="string_compare",
                            description="String character comparison in nested loops",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.30,
                        )
                    )

    def _find_grid_lookback(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Subscript):
                    outer_name = None
                    if isinstance(node.value.value, ast.Name):
                        outer_name = node.value.value.id.lower()
                    if outer_name and outer_name.startswith("dp"):
                        inner_slice = node.value.slice
                        outer_slice = node.slice
                        if isinstance(inner_slice, ast.BinOp) and isinstance(inner_slice.op, ast.Sub):
                            return True
                        if isinstance(outer_slice, ast.BinOp) and isinstance(outer_slice.op, ast.Sub):
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
                        if isinstance(target.value, ast.Name) and target.value.id.lower().startswith("dp"):
                            if isinstance(target.slice, ast.Subscript):
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
                                if isinstance(inner_list, ast.List) or (
                                    isinstance(inner_list, ast.BinOp) and isinstance(inner_list.op, ast.Mult)
                                ):
                                    return True
        return False

    def _find_recurrence_expression(self, func_def: ast.FunctionDef) -> bool:
        has_max_min = False
        has_grid_lookback = False
        for node in ast.walk(func_def):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("max", "min"):
                    has_max_min = True
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Subscript):
                    if isinstance(node.value.value, ast.Name) and node.value.value.id.lower().startswith("dp"):
                        slice1 = node.value.slice
                        slice2 = node.slice
                        if isinstance(slice1, ast.BinOp) or isinstance(slice2, ast.BinOp):
                            has_grid_lookback = True
        return has_max_min and has_grid_lookback

    def _find_result_aggregation(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Return):
                if isinstance(node.value, ast.Subscript):
                    if isinstance(node.value.value, ast.Subscript):
                        if isinstance(node.value.value.value, ast.Name) and node.value.value.value.id.lower().startswith("dp"):
                            return True
                    if isinstance(node.value.value, ast.Name) and node.value.value.id.lower().startswith("dp"):
                        if isinstance(node.value.slice, ast.UnaryOp) or isinstance(node.value.slice, ast.Constant):
                            return True
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name) and node.value.func.id in ("max", "min"):
                        for arg in node.value.args:
                            if isinstance(arg, ast.Name) and arg.id.lower().startswith("dp"):
                                return True
        return False

    def _find_base_case(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Compare):
                    for side in [node.test.left] + node.test.comparators:
                        if isinstance(side, ast.Name) and side.id.lower() in ("r", "c", "row", "col", "i", "j"):
                            for stmt in node.body:
                                if isinstance(stmt, ast.Assign):
                                    return True
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
                                    if name.startswith(("s", "str", "word", "text", "char")):
                                        return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
