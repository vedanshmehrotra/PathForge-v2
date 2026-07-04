"""Detector for knapsack DP pattern.

Detects structural evidence of knapsack-style dynamic programming where
a table is filled with capacity as one dimension and items as the other.
Characteristic of 0/1 Knapsack, Unbounded Knapsack, Partition Equal
Subset Sum, Coin Change (as knapsack), Target Sum.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class DPKnapsackDetector(BaseDetector):
    pattern_id = "dp_knapsack"

    WEIGHT_VARS = {"weight", "weights", "w", "wt", "capacity", "cap", "c", "amount", "amt", "target"}

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_knapsack(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_capacity = any(e.type == "capacity_compare" for e in evidence)
        has_max_min = any(e.type == "max_min_recurrence" for e in evidence)
        has_array = any(e.type == "dp_array_2d" for e in evidence)
        has_nested = any(e.type == "nested_fill_loops" for e in evidence)
        has_lookback = any(e.type == "grid_lookback" for e in evidence)

        secondary_count = sum([has_array, has_nested, has_lookback])
        detected = has_capacity and has_max_min and secondary_count >= 1

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_knapsack(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if isinstance(node, ast.FunctionDef):
                has_capacity = self._find_capacity_compare(node)
                has_max_min = self._find_max_min_recurrence(node)
                has_array = self._find_dp_array_2d(node)
                has_nested = self._find_nested_fill_loops(node)
                has_lookback = self._find_grid_lookback(node)
                has_aggregation = self._find_result_aggregation(node)

                if has_capacity:
                    evidence.append(
                        EvidenceItem(
                            type="capacity_compare",
                            description="Capacity vs weight comparison in if-statement",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.30,
                        )
                    )

                if has_max_min:
                    evidence.append(
                        EvidenceItem(
                            type="max_min_recurrence",
                            description="Max/min recurrence with DP lookback and value/weight",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )

                if has_array:
                    evidence.append(
                        EvidenceItem(
                            type="dp_array_2d",
                            description="2D DP array for knapsack items and capacity",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )

                if has_nested:
                    evidence.append(
                        EvidenceItem(
                            type="nested_fill_loops",
                            description="Two-level nested loop: items outer, capacity inner",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.20,
                        )
                    )

                if has_lookback:
                    evidence.append(
                        EvidenceItem(
                            type="grid_lookback",
                            description="Grid lookback dp[i-1][c], dp[i-1][c-w[i]]",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.20,
                        )
                    )

                if has_aggregation:
                    evidence.append(
                        EvidenceItem(
                            type="result_aggregation",
                            description="Result aggregation returning dp[-1][cap]",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.15,
                        )
                    )

    def _find_capacity_compare(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Compare):
                    ops = node.test.ops
                    if any(isinstance(op, (ast.GtE, ast.Gt, ast.LtE, ast.Lt)) for op in ops):
                        for side in [node.test.left] + node.test.comparators:
                            if isinstance(side, ast.Name) and side.id.lower() in self.WEIGHT_VARS:
                                return True
                            if isinstance(side, ast.Subscript):
                                if isinstance(side.value, ast.Name):
                                    name = side.value.id.lower()
                                    if name in self.WEIGHT_VARS or "weight" in name or name in ("weights", "coins", "nums"):
                                        return True
        return False

    def _find_max_min_recurrence(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("max", "min"):
                    has_dp_arg = False
                    for arg in node.args:
                        has_dp_arg = self._has_dp_reference(arg) or has_dp_arg
                    if has_dp_arg:
                        return True
            if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.Or, ast.And)):
                has_dp_arg = False
                for val in node.values:
                    has_dp_arg = self._has_dp_reference(val) or has_dp_arg
                if has_dp_arg:
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

    def _find_dp_array_2d(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.ListComp):
                    for generator in node.value.generators:
                        if isinstance(generator.iter, ast.Call):
                            if isinstance(generator.iter.func, ast.Name) and generator.iter.func.id == "range":
                                if isinstance(node.value.elt, (ast.List, ast.BinOp)):
                                    return True
        return False

    def _find_nested_fill_loops(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.For):
                for child in ast.walk(node):
                    if isinstance(child, ast.For) and child is not node:
                        has_dp_write = self._has_dp_write(child)
                        if has_dp_write:
                            return True
        return False

    def _has_dp_write(self, loop_node: ast.For) -> bool:
        for node in ast.walk(loop_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Subscript):
                        cur = target
                        while isinstance(cur, ast.Subscript):
                            if isinstance(cur.value, ast.Name) and cur.value.id.lower().startswith("dp"):
                                return True
                            cur = cur.value
        return False

    def _find_grid_lookback(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Subscript):
                    if isinstance(node.value.value, ast.Name) and node.value.value.id.lower().startswith("dp"):
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

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
