"""Detector for 1D forward DP pattern.

Detects structural evidence of 1D forward dynamic programming where a
single array is filled left-to-right using a recurrence that depends on
a fixed number of previous elements. Characteristic of Climbing Stairs,
House Robber, Fibonacci-style DP, and 1D cost/min-path problems.

Supports space-optimized DP (rolling variables, O(1) state transitions)
as valid DP even without explicit dp array creation.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class DP1DForwardDetector(BaseDetector):
    pattern_id = "dp_1d_forward"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_1d_forward(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_index_lookback = any(e.type == "index_lookback" for e in evidence)
        has_recursive_lookback = any(e.type == "recursive_lookback" for e in evidence)
        has_dp_array_1d = any(e.type == "dp_array_1d" for e in evidence)
        has_table_fill_loop = any(e.type == "table_fill_loop" for e in evidence)
        has_cache = any(e.type == "cache_decorator" for e in evidence)
        has_recurrence = any(e.type == "recurrence_expression" for e in evidence)
        has_base_case = any(e.type == "base_case_return" for e in evidence)

        has_multi_lookback = any(e.type == "multi_level_lookback" for e in evidence)
        has_conditional = any(e.type == "conditional_recurrence" for e in evidence)
        has_max_min = any(e.type == "max_min_recurrence" for e in evidence)

        secondary_count = sum([has_dp_array_1d, has_table_fill_loop, has_cache, has_base_case])
        effective_lookback = has_index_lookback or has_recursive_lookback
        detected = effective_lookback and secondary_count >= 2

        if self._has_anti_signals(evidence):
            detected = False

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_1d_forward(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if isinstance(node, ast.FunctionDef):
                has_array = self._find_dp_array_1d(node)
                has_loop = self._find_table_fill_loop(node)
                lookback_count = self._count_lookback_levels(node)
                has_lookback = lookback_count >= 1
                has_multi = lookback_count >= 2
                has_cache = self._find_cache_decorator(node)
                has_recurrence = self._find_recurrence_expression(node)
                has_max_min = self._find_max_min_recurrence(node)
                has_base_case = self._find_base_case(node)
                has_aggregation = self._find_result_aggregation(node)
                has_conditional = self._find_conditional_recurrence(node)
                has_recursive = self._find_recursive_lookback(node)

                if has_array:
                    evidence.append(
                        EvidenceItem(
                            type="dp_array_1d",
                            description="1D DP array created via list multiplication",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )

                if has_loop:
                    evidence.append(
                        EvidenceItem(
                            type="table_fill_loop",
                            description="For-loop filling DP array with index writes",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.20,
                        )
                    )

                if has_lookback:
                    evidence.append(
                        EvidenceItem(
                            type="index_lookback",
                            description="Index lookback dp[i-1], dp[i-2] read during table fill",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.30,
                        )
                    )

                if has_multi:
                    evidence.append(
                        EvidenceItem(
                            type="multi_level_lookback",
                            description="Multi-level index lookback at two or more levels deep",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.0,
                        )
                    )

                if has_recursive:
                    evidence.append(
                        EvidenceItem(
                            type="recursive_lookback",
                            description="Recursive calls with arithmetic arguments (memoized subproblem lookback)",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )

                if has_cache:
                    evidence.append(
                        EvidenceItem(
                            type="cache_decorator",
                            description="Cache decorator on recursive function",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.30,
                        )
                    )

                if has_recurrence:
                    evidence.append(
                        EvidenceItem(
                            type="recurrence_expression",
                            description="Recurrence expression combining lookback terms via arithmetic",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.20,
                        )
                    )

                if has_max_min:
                    evidence.append(
                        EvidenceItem(
                            type="max_min_recurrence",
                            description="Max/min recurrence expression combining multiple subproblem results",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.20,
                        )
                    )

                if has_base_case:
                    evidence.append(
                        EvidenceItem(
                            type="base_case_return",
                            description="Base case return for n <= 1 or boundary initialization",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.15,
                        )
                    )

                if has_aggregation:
                    evidence.append(
                        EvidenceItem(
                            type="result_aggregation",
                            description="Result aggregation via return dp[n] or dp[-1]",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.15,
                        )
                    )

                if has_conditional:
                    evidence.append(
                        EvidenceItem(
                            type="conditional_recurrence",
                            description="Conditional branching in recurrence, not pure accumulation",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.0,
                        )
                    )

    def _find_dp_array_1d(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Assign):
                if isinstance(child.value, ast.BinOp) and isinstance(child.value.op, ast.Mult):
                    if isinstance(child.value.left, ast.List):
                        return True
        return False

    def _find_table_fill_loop(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.For):
                has_nested = False
                for sub in ast.walk(child):
                    if isinstance(sub, ast.For) and sub is not child:
                        has_nested = True
                        break
                if has_nested:
                    continue
                has_dp_write = self._has_dp_subscript_write(child)
                if has_dp_write:
                    return True
        return False

    def _has_dp_subscript_write(self, loop_node: ast.For) -> bool:
        for node in ast.walk(loop_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Subscript):
                        if isinstance(target.value, ast.Name) and target.value.id.lower().startswith("dp"):
                            return True
        return False

    def _count_lookback_levels(self, func_def: ast.FunctionDef) -> int:
        levels = set()
        for node in ast.walk(func_def):
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Name) and node.value.id.lower().startswith("dp"):
                    if isinstance(node.slice, ast.BinOp) and isinstance(node.slice.op, ast.Sub):
                        if isinstance(node.slice.right, ast.Constant):
                            offset = node.slice.right.value
                            if isinstance(offset, int):
                                levels.add(offset)
                        elif isinstance(node.slice.left, ast.Constant):
                            offset = node.slice.left.value
                            if isinstance(offset, int):
                                levels.add(offset)
        return len(levels)

    def _find_cache_decorator(self, func_def: ast.FunctionDef) -> bool:
        for decorator in func_def.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id in ("cache", "lru_cache"):
                return True
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id in ("cache", "lru_cache"):
                    return True
                if isinstance(decorator.func, ast.Attribute) and decorator.func.attr in ("cache", "lru_cache"):
                    return True
            if isinstance(decorator, ast.Attribute) and decorator.attr in ("cache", "lru_cache"):
                return True
        return False

    def _find_recurrence_expression(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
                has_dp_lookback = False
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Subscript):
                        if isinstance(sub.value, ast.Name) and sub.value.id.lower().startswith("dp"):
                            has_dp_lookback = True
                if has_dp_lookback:
                    return True
        return False

    def _find_max_min_recurrence(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("max", "min"):
                    return True
        return False

    def _find_base_case(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Compare):
                    for side in [node.test.left] + node.test.comparators:
                        if isinstance(side, ast.Name) and side.id.lower() in ("n", "i", "idx", "index"):
                            for stmt in node.body:
                                if isinstance(stmt, ast.Return):
                                    return True
        return False

    def _find_result_aggregation(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Return):
                if isinstance(node.value, ast.Subscript):
                    if isinstance(node.value.value, ast.Name) and node.value.value.id.lower().startswith("dp"):
                        return True
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name) and node.value.func.id in ("max", "min"):
                        for arg in node.value.args:
                            if isinstance(arg, ast.Name) and arg.id.lower().startswith("dp"):
                                return True
        return False

    def _find_conditional_recurrence(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.If):
                for side in [node.test.left]:
                    if isinstance(side, ast.Name) and side.id.lower() in ("i", "j", "n", "idx"):
                        for stmt in node.body:
                            if isinstance(stmt, ast.Assign):
                                for target in stmt.targets:
                                    if isinstance(target, ast.Subscript):
                                        if isinstance(target.value, ast.Name) and target.value.id.lower().startswith("dp"):
                                            return True
                    if isinstance(side, ast.Subscript):
                        if isinstance(side.value, ast.Name) and side.value.id.lower().startswith("dp"):
                            return True
        return False

    def _find_recursive_lookback(self, func_def: ast.FunctionDef) -> bool:
        """Detect recursive calls with arithmetic on parameters (memoized subproblem lookback)."""
        func_name = func_def.name
        has_recursive_call = False
        has_arithmetic_arg = False
        for node in ast.walk(func_def):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == func_name:
                    has_recursive_call = True
                    for arg in node.args:
                        if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub):
                            has_arithmetic_arg = True
        return has_recursive_call and has_arithmetic_arg

    def _has_anti_signals(self, evidence: list) -> bool:
        has_index_lookback = any(e.type == "index_lookback" for e in evidence)
        has_multi_lookback = any(e.type == "multi_level_lookback" for e in evidence)
        has_max_min = any(e.type == "max_min_recurrence" for e in evidence)
        has_conditional = any(e.type == "conditional_recurrence" for e in evidence)
        has_recursive_lookback = any(e.type == "recursive_lookback" for e in evidence)
        is_prefix_sum = has_index_lookback and not (has_multi_lookback or has_max_min or has_conditional or has_recursive_lookback)
        if is_prefix_sum:
            return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
