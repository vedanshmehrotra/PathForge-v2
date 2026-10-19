"""Detector for prefix sum pattern.

Detects running cumulative sums, prefix array construction,
and hash-map-based prefix sum lookups (subarray sum patterns).

Prefix products are a different operation; their suitability is independent of
this detector's additive evidence. Multiplication inside an incoming term may
still form a weighted sum, but multiplying the accumulated prefix does not.

Does NOT detect sliding window or other non-cumulative patterns.
"""

import ast
from src.ast_detection.python_structure import bindings, scope_nodes
from src.ast_detection.window_structure import same
from typing import Set
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class PrefixSumDetector(BaseDetector):
    pattern_id = "prefix_sum"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_prefix_array(ast_root, evidence)
        self._detect_running_sum(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=confidence > 0.0,
        )


    def _detect_prefix_array(self, ast_root, evidence):
        """One destination extends its own previous prefix; another row cannot supply it."""
        def offset(value, index):
            if isinstance(value, ast.Name) and value.id == index:
                return 0
            if (isinstance(value, ast.BinOp) and isinstance(value.left, ast.Name)
                    and value.left.id == index and isinstance(value.right, ast.Constant)
                    and type(value.right.value) is int and isinstance(value.op, (ast.Add, ast.Sub))):
                return value.right.value * (1 if isinstance(value.op, ast.Add) else -1)
            return None

        for loop in ast.walk(ast_root):
            if not isinstance(loop, ast.For) or not isinstance(loop.target, ast.Name):
                continue
            for statement in loop.body:
                destination = previous_index = value = None
                if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                    target = statement.targets[0]
                    if isinstance(target, ast.Subscript):
                        destination, value = target.value, statement.value
                        previous_index = offset(target.slice, loop.target.id)
                elif isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
                    call = statement.value
                    if (isinstance(call.func, ast.Attribute) and call.func.attr == 'append'
                            and len(call.args) == 1 and not call.keywords):
                        destination, value = call.func.value, call.args[0]
                if not (destination is not None and isinstance(value, ast.BinOp)
                        and isinstance(value.op, (ast.Add, ast.Sub))
                        and isinstance(value.left, ast.Subscript) and same(value.left.value, destination)):
                    continue
                if isinstance(destination, ast.Name) and bindings(loop.body, destination.id):
                    continue
                if isinstance(destination, ast.Attribute) and any(
                    isinstance(n, ast.Attribute) and isinstance(n.ctx, (ast.Store, ast.Del))
                    and ast.unparse(n) == ast.unparse(destination) for n in scope_nodes(loop.body)):
                    continue
                previous = value.left.slice
                if previous_index is None:
                    linked = (isinstance(statement, ast.Expr) and isinstance(previous, ast.UnaryOp)
                              and isinstance(previous.op, ast.USub) and isinstance(previous.operand, ast.Constant)
                              and previous.operand.value == 1)
                else:
                    old_index = offset(previous, loop.target.id)
                    linked = old_index is not None and previous_index - old_index == 1
                # A recurrence on the same state (Fibonacci/DP), or an append
                # using somebody else's last item, does not construct a prefix.
                if not linked or any(isinstance(n, ast.Subscript) and same(n.value, destination)
                                     for n in ast.walk(value.right)):
                    continue
                evidence.extend([
                    EvidenceItem(type='prefix_array_construction', description='Destination extends its own preceding additive prefix',
                                 location=f'{statement.lineno}:{statement.col_offset}', weight=0.40),
                    EvidenceItem(type='prefix_accumulator', description='Cumulative state and additive input are linked',
                                 location=f'{statement.lineno}:{statement.col_offset}', weight=0.30)])
                break

    def _detect_running_sum(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: running sum variable with dictionary lookup pattern.

        Matches:
            running_sum = 0
            seen = {}
            for num in arr:
                running_sum += num
                if running_sum - k in seen:
                    count += 1
                seen[running_sum] = index
        """
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.For):
                continue

            running_vars = self._find_running_sum_vars(node)
            if not running_vars:
                continue

            has_dict_store = self._find_dict_store(node.body, running_vars)
            has_dict_lookup = self._find_dict_lookup(node.body, running_vars)

            if has_dict_lookup or has_dict_store:
                evidence.append(
                    EvidenceItem(
                        type="running_sum_update",
                        description=f"Running sum '{', '.join(running_vars)}' updated in loop",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )
                if has_dict_store:
                    evidence.append(
                        EvidenceItem(
                            type="dictionary_prefix_lookup",
                            description="Prefix sums stored in dictionary for O(1) lookup",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.35,
                        )
                    )


    def _find_running_sum_vars(self, for_node: ast.For) -> Set[str]:
        """Find variables being augmented with += in the loop body."""
        vars_found = set()
        for stmt in for_node.body:
            if isinstance(stmt, ast.AugAssign):
                if isinstance(stmt.op, ast.Add) and isinstance(stmt.target, ast.Name):
                    vars_found.add(stmt.target.id)
        if isinstance(for_node.orelse, list):
            for stmt in for_node.orelse:
                if isinstance(stmt, ast.AugAssign):
                    if isinstance(stmt.op, ast.Add) and isinstance(stmt.target, ast.Name):
                        vars_found.add(stmt.target.id)
        return vars_found

    def _walk_body(self, body: list):
        """Walk over all nodes in a body list safely."""
        yield from scope_nodes(body)

    def _find_dict_store(self, body: list, running_vars: Set[str]) -> bool:
        """Check if running sum values are stored in a dictionary."""
        for stmt in self._walk_body(body):
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Subscript):
                        if isinstance(target.value, ast.Dict):
                            return True
                        if isinstance(target.value, ast.Name) and target.value.id not in running_vars:
                            for var in running_vars:
                                if self._contains_name(stmt.value, var):
                                    return True
            if isinstance(stmt, ast.Subscript):
                if isinstance(stmt.value, ast.Name) and stmt.value.id not in running_vars:
                    if isinstance(stmt.slice, ast.Name) and stmt.slice.id in running_vars:
                        return True
        return False

    def _find_dict_lookup(self, body: list, running_vars: Set[str]) -> bool:
        """Check if running sum participates in dictionary lookup."""
        for stmt in self._walk_body(body):
            if isinstance(stmt, ast.If):
                test = stmt.test
                for subnode in ast.walk(test):
                    if isinstance(subnode, ast.Subscript):
                        if (isinstance(subnode.value, ast.Name) and subnode.value.id not in running_vars
                                and any(self._contains_name(subnode.slice, var) for var in running_vars)):
                            return True
                    if isinstance(subnode, ast.BinOp) and isinstance(subnode.op, ast.Sub):
                        if isinstance(subnode.left, ast.Name) and subnode.left.id in running_vars:
                            return True
                    if isinstance(subnode, ast.Call):
                        if (isinstance(subnode.func, ast.Attribute) and subnode.func.attr == "get" and subnode.args
                                and any(self._contains_name(subnode.args[0], var) for var in running_vars)):
                            return True
        return False

    @staticmethod
    def _contains_name(node: ast.AST, name: str) -> bool:
        for subnode in ast.walk(node):
            if isinstance(subnode, ast.Name) and subnode.id == name:
                return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
