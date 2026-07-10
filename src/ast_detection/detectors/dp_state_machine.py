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

        if self._has_anti_signals(evidence):
            detected = False

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
        loop_assigned = set()
        dp_subscript_writes = {}
        for node in ast.walk(func_def):
            if isinstance(node, (ast.For, ast.While)):
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Assign):
                        for target in sub.targets:
                            self._collect_assigned_names(target, loop_assigned, dp_subscript_writes, node)

        max_min_args = set()
        for node in ast.walk(func_def):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("max", "min"):
                    for arg in node.args:
                        if isinstance(arg, ast.Name):
                            max_min_args.add(arg.id)
                        elif isinstance(arg, ast.Subscript):
                            base = self._get_subscript_base(arg)
                            if base:
                                max_min_args.add(base)
                        elif isinstance(arg, ast.BinOp):
                            for sub in ast.walk(arg):
                                if isinstance(sub, ast.Name):
                                    max_min_args.add(sub.id)
                                elif isinstance(sub, ast.Subscript):
                                    base = self._get_subscript_base(sub)
                                    if base:
                                        max_min_args.add(base)

        state_candidates = loop_assigned & max_min_args
        if len(state_candidates) >= 2:
            return True

        for base, count in dp_subscript_writes.items():
            if count >= 2 and base in max_min_args:
                return True

        return False

    def _collect_assigned_names(self, target: ast.AST, names: set, dp_writes: dict, loop_node: ast.AST) -> None:
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, ast.Tuple):
            for elt in target.elts:
                self._collect_assigned_names(elt, names, dp_writes, loop_node)
        elif isinstance(target, ast.Subscript):
            base = self._get_subscript_base(target)
            if base:
                names.add(base)
                dp_writes[base] = dp_writes.get(base, 0) + 1

    def _get_subscript_base(self, node: ast.AST) -> str:
        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name):
                return node.value.id
            if isinstance(node.value, ast.Subscript):
                return self._get_subscript_base(node.value)
        return None

    def _find_state_transition(self, func_def: ast.FunctionDef) -> bool:
        loop_vars = self._collect_loop_assigned_vars(func_def)
        for node in ast.walk(func_def):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("max", "min"):
                    has_state_arg = False
                    for arg in node.args:
                        if self._references_any_variable(arg, loop_vars):
                            has_state_arg = True
                            break
                    if not has_state_arg:
                        continue
                    for stmt in ast.walk(func_def):
                        if isinstance(stmt, ast.Assign):
                            target_vars = set()
                            self._collect_target_vars(stmt.targets, target_vars, loop_vars)
                            if target_vars:
                                if stmt.value is node or any(
                                    isinstance(n, ast.Call) and n is node
                                    for n in ast.walk(stmt.value)
                                    if isinstance(n, ast.Call)
                                ):
                                    target_var = next(iter(target_vars))
                                    if self._has_state_on_left_of_binop(node, target_var, loop_vars):
                                        return True
        return False

    def _has_state_on_left_of_binop(self, call_node: ast.Call, target_var: str, loop_vars: set) -> bool:
        """Check if the max/min call references another state variable on the left side
        of a BinOp arg, or as a direct Subscript arg.

        Genuine state machines write:  state = max(state, OTHER_STATE + value)
                                       state = max(state, other_array[i], ...)
        Running max patterns write:    var = max(var, value - var)   (state on the RIGHT)
        """
        for arg in call_node.args:
            if isinstance(arg, ast.Name) and arg.id == target_var:
                continue
            if isinstance(arg, ast.BinOp):
                if self._left_side_contains_other_state(arg, target_var, loop_vars):
                    return True
            if isinstance(arg, ast.Name) and arg.id in loop_vars and arg.id != target_var:
                return True
            if isinstance(arg, ast.Subscript):
                base = self._get_subscript_base(arg)
                if base and base in loop_vars:
                    return True
        return False

    def _left_side_contains_other_state(self, node: ast.AST, target_var: str, loop_vars: set) -> bool:
        """Recursively check only the LEFT branch of BinOps for a different state variable.

        Genuine state machines write:  other_state + reward
        Running max patterns write:    value - var   (state on the RIGHT, not LEFT)
        """
        if isinstance(node, ast.BinOp):
            return self._left_side_contains_other_state(node.left, target_var, loop_vars)
        if isinstance(node, ast.Name) and node.id in loop_vars and node.id != target_var:
            return True
        if isinstance(node, ast.Subscript):
            base = self._get_subscript_base(node)
            if base and base in loop_vars and base != target_var:
                return True
        return False

    def _collect_target_vars(self, targets: list, result: set, loop_vars: set) -> None:
        for target in targets:
            if isinstance(target, ast.Name) and target.id in loop_vars:
                result.add(target.id)
            elif isinstance(target, ast.Tuple):
                for elt in target.elts:
                    if isinstance(elt, ast.Name) and elt.id in loop_vars:
                        result.add(elt.id)
            elif isinstance(target, ast.Subscript):
                base = self._get_subscript_base(target)
                if base and (base in loop_vars or base.lower().startswith("dp")):
                    result.add(base)

    def _collect_loop_assigned_vars(self, func_def: ast.FunctionDef) -> set:
        vars_set = set()
        for node in ast.walk(func_def):
            if isinstance(node, (ast.For, ast.While)):
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Assign):
                        for target in sub.targets:
                            self._collect_names_from_target(target, vars_set, None, None)
        return vars_set

    def _collect_names_from_target(self, target: ast.AST, names: set, dp_writes: dict, loop_node: ast.AST) -> None:
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, ast.Tuple):
            for elt in target.elts:
                self._collect_names_from_target(elt, names, dp_writes, loop_node)
        elif isinstance(target, ast.Subscript):
            base = self._get_subscript_base(target)
            if base:
                names.add(base)

    def _references_any_variable(self, node: ast.AST, vars_set: set) -> bool:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and sub.id in vars_set:
                return True
            if isinstance(sub, ast.Subscript):
                base = self._get_subscript_base(sub)
                if base and base in vars_set:
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
                            if isinstance(arg, ast.Name):
                                return True
                            if isinstance(arg, ast.Subscript):
                                if isinstance(arg.value, ast.Name):
                                    return True
        return False

    def _has_anti_signals(self, evidence: list) -> bool:
        has_state_vars = any(e.type == "state_variables" for e in evidence)
        has_transition = any(e.type == "state_transition" for e in evidence)
        if has_state_vars and not has_transition:
            return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
