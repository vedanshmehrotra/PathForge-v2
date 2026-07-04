"""Detector for state machine DP pattern.

Detects structural evidence of state-machine dynamic programming where
a fixed, small number of states (typically 2-4) are tracked across
iterations. Characteristic of Best Time to Buy/Sell Stock with Cooldown,
House Robber (cyclic or with constraints), and Paint House.

Supports both explicit dp array and pure state variable implementations.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class DPStateMachineDetector(BaseDetector):
    pattern_id = "dp_state_machine"

    STATE_NAMES = {
        "hold", "sold", "rest", "cooldown", "buy", "sell",
        "prev0", "prev1", "curr0", "curr1",
        "prev_hold", "prev_sold", "prev_rest",
        "dp0", "dp1", "dp2",
        "cash", "stock", "state",
        "not_hold", "hold_stock",
        "with_stock", "without_stock",
        "has_stock", "no_stock",
        "keep", "take",
        "rob_prev", "rob_curr",
        "rob0", "rob1",
        "prev_rob", "curr_rob",
        "max0", "max1",
        "prev_take", "prev_skip",
        "take_curr", "skip_curr",
        "taken", "skipped",
        "buy_state", "sell_state",
        "prev_max", "curr_max", "prev_buy", "prev_sell",
    }

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_state_machine(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_state_vars = any(e.type == "state_variables" for e in evidence)
        has_state_transition = any(e.type == "state_transition" for e in evidence)
        has_dp_array_1d = any(e.type == "dp_array_1d" for e in evidence)
        has_loop = any(e.type == "table_fill_loop" for e in evidence)
        has_cache = any(e.type == "cache_decorator" for e in evidence)

        secondary_count = sum([has_dp_array_1d, has_loop, has_cache])
        detected = has_state_vars and has_state_transition and secondary_count >= 1

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_state_machine(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if isinstance(node, ast.FunctionDef):
                has_vars = self._find_state_variables(node)
                has_transition = self._find_state_transition(node)
                has_array = self._find_small_dp_array(node)
                has_loop = self._find_single_loop(node)
                has_cache = self._find_cache_decorator(node)
                has_aggregation = self._find_result_aggregation(node)

                if has_vars:
                    evidence.append(
                        EvidenceItem(
                            type="state_variables",
                            description="Multiple named state variables detected",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.30,
                        )
                    )

                if has_transition:
                    evidence.append(
                        EvidenceItem(
                            type="state_transition",
                            description="State transition via max/min between competing states",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.30,
                        )
                    )

                if has_array:
                    evidence.append(
                        EvidenceItem(
                            type="dp_array_1d",
                            description="Small fixed-size DP array for state machine",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.20,
                        )
                    )

                if has_loop:
                    evidence.append(
                        EvidenceItem(
                            type="table_fill_loop",
                            description="Single loop iterating over input, updating states",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.20,
                        )
                    )

                if has_cache:
                    evidence.append(
                        EvidenceItem(
                            type="cache_decorator",
                            description="Cache decorator on recursive state machine function",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.30,
                        )
                    )

                if has_aggregation:
                    evidence.append(
                        EvidenceItem(
                            type="result_aggregation",
                            description="Result aggregation via max of states",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.20,
                        )
                    )

    def _find_state_variables(self, func_def: ast.FunctionDef) -> bool:
        state_assignments = set()

        for node in ast.walk(func_def):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id.lower() in self.STATE_NAMES:
                            state_assignments.add(target.id.lower())
                    if isinstance(target, ast.Subscript):
                        if isinstance(target.value, ast.Name):
                            if target.value.id.lower() in self.STATE_NAMES:
                                state_assignments.add(target.value.id.lower())
                        if isinstance(target.value, ast.Subscript):
                            if isinstance(target.value.value, ast.Name):
                                base = target.value.value.id.lower()
                                if base.startswith("dp"):
                                    if isinstance(target.value.slice, ast.Name):
                                        state_assignments.add(f"dp_{target.value.slice.id}")
                                    elif isinstance(target.value.slice, ast.Constant):
                                        state_assignments.add(f"dp_{target.value.slice.value}")
                                if base.startswith("dp"):
                                    slice_val = None
                                    if isinstance(target.slice, ast.Name):
                                        slice_val = target.slice.id
                                    elif isinstance(target.slice, ast.Constant):
                                        slice_val = str(target.slice.value)
                                    if slice_val is not None:
                                        state_assignments.add(f"dp_val_{slice_val}")

            if isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Name):
                    if node.target.id.lower() in self.STATE_NAMES:
                        state_assignments.add(node.target.id.lower())

        if len(state_assignments) >= 2:
            return True

        max_min_on_state_count = 0
        for node in ast.walk(func_def):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("max", "min"):
                    state_args = 0
                    for arg in node.args:
                        if isinstance(arg, ast.Name) and arg.id.lower() in self.STATE_NAMES:
                            state_args += 1
                        if isinstance(arg, ast.Subscript):
                            if isinstance(arg.value, ast.Name) and arg.value.id.lower() in self.STATE_NAMES:
                                state_args += 1
                    if state_args >= 2:
                        max_min_on_state_count += 1

        return max_min_on_state_count >= 1

    def _find_state_transition(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("max", "min"):
                    state_args = 0
                    binop_with_state = False
                    for arg in node.args:
                        if isinstance(arg, ast.Name) and arg.id.lower() in self.STATE_NAMES:
                            state_args += 1
                        if isinstance(arg, ast.Subscript):
                            if isinstance(arg.value, ast.Name) and arg.value.id.lower() in self.STATE_NAMES:
                                state_args += 1
                            if isinstance(arg.value, ast.Subscript):
                                if isinstance(arg.value.value, ast.Name) and arg.value.value.id.lower().startswith("dp"):
                                    state_args += 1
                        if isinstance(arg, ast.BinOp):
                            for sub in ast.walk(arg):
                                if isinstance(sub, ast.Name) and sub.id.lower() in self.STATE_NAMES:
                                    binop_with_state = True
                                if isinstance(sub, ast.Subscript):
                                    if isinstance(sub.value, ast.Name) and sub.value.id.lower() in self.STATE_NAMES:
                                        binop_with_state = True
                                    if isinstance(sub.value, ast.Subscript):
                                        if isinstance(sub.value.value, ast.Name) and sub.value.value.id.lower().startswith("dp"):
                                            binop_with_state = True
                    if state_args >= 1 or binop_with_state:
                        for stmt in ast.walk(func_def):
                            if isinstance(stmt, ast.Assign):
                                for target in stmt.targets:
                                    if isinstance(target, ast.Name) and target.id.lower() in self.STATE_NAMES:
                                        if stmt.value is node or any(
                                            isinstance(n, ast.Call) and n is node
                                            for n in ast.walk(stmt.value)
                                            if isinstance(n, ast.Call)
                                        ):
                                            return True
                                    if isinstance(target, ast.Subscript):
                                        if isinstance(target.value, ast.Name) and target.value.id.lower() in self.STATE_NAMES:
                                            if stmt.value is node or any(
                                                isinstance(n, ast.Call) and n is node
                                                for n in ast.walk(stmt.value)
                                                if isinstance(n, ast.Call)
                                            ):
                                                return True
                                        if isinstance(target.value, ast.Subscript):
                                            if isinstance(target.value.value, ast.Name) and target.value.value.id.lower().startswith("dp"):
                                                if stmt.value is node or any(
                                                    isinstance(n, ast.Call) and n is node
                                                    for n in ast.walk(stmt.value)
                                                    if isinstance(n, ast.Call)
                                                ):
                                                    return True
        return False

    def _find_small_dp_array(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Mult):
                    if isinstance(node.value.left, ast.List) and isinstance(node.value.right, ast.Constant):
                        if isinstance(node.value.right.value, int) and 2 <= node.value.right.value <= 4:
                            return True
                    if isinstance(node.value.left, ast.List) and isinstance(node.value.right, ast.UnaryOp):
                        return True
        return False

    def _find_single_loop(self, func_def: ast.FunctionDef) -> bool:
        has_single_loop = False
        has_nested = False
        for node in ast.walk(func_def):
            if isinstance(node, ast.For):
                if self._is_nested_for(node, func_def):
                    has_nested = True
                else:
                    has_single_loop = True
        return has_single_loop and not has_nested

    def _is_nested_for(self, target: ast.For, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.For) and node is not target:
                for child in ast.walk(node):
                    if child is target:
                        return True
        return False

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

    def _find_result_aggregation(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Return):
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name) and node.value.func.id in ("max", "min"):
                        for arg in node.value.args:
                            if isinstance(arg, ast.Name) and arg.id.lower() in self.STATE_NAMES:
                                return True
                            if isinstance(arg, ast.Subscript):
                                if isinstance(arg.value, ast.Name) and arg.value.id.lower() in self.STATE_NAMES:
                                    return True
                                if isinstance(arg.value, ast.Name) and arg.value.id.lower().startswith("dp"):
                                    return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
