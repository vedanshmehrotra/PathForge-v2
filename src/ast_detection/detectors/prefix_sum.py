"""Detector for prefix sum pattern.

Detects running cumulative sums, prefix array construction,
and hash-map-based prefix sum lookups (subarray sum patterns).

Does NOT detect sliding window or other non-cumulative patterns.
"""

import ast
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

    def _detect_prefix_array(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: prefix array construction with cumulative formula or append pattern.

        Matches:
            prefix = [0] * (n + 1)
            for i in range(1, n + 1):
                prefix[i] = prefix[i - 1] + arr[i - 1]

            prefix = [0]
            for num in nums:
                prefix.append(prefix[-1] + num)
        """
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.For):
                continue

            if not isinstance(node.target, ast.Name):
                continue

            prefix_names = self._find_prefix_array_targets(node.body)
            has_append = self._find_append_to_list(node.body)

            if not prefix_names and not has_append:
                continue

            has_prefix_formula = False
            has_accumulator = False
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Subscript):
                            if isinstance(target.value, ast.Name) and (target.value.id in prefix_names or has_append):
                                value = stmt.value
                                if isinstance(value, ast.BinOp) and isinstance(value.op, (ast.Add, ast.Mult, ast.Sub)):
                                    left = value.left
                                    if isinstance(left, ast.Subscript):
                                        has_prefix_formula = True
                call_node = stmt
                if isinstance(stmt, ast.Expr):
                    call_node = stmt.value
                if isinstance(call_node, ast.Call):
                    if isinstance(call_node.func, ast.Attribute) and call_node.func.attr == "append":
                        for arg in call_node.args:
                            if isinstance(arg, ast.BinOp) and isinstance(arg.op, (ast.Add, ast.Mult, ast.Sub)):
                                for sub in ast.walk(arg):
                                    if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name):
                                        has_prefix_formula = True

            for stmt in node.body:
                if isinstance(stmt, ast.AugAssign):
                    if isinstance(stmt.op, (ast.Add, ast.Mult, ast.Sub)):
                        has_accumulator = True

            if has_prefix_formula or has_accumulator:
                evidence.append(
                    EvidenceItem(
                        type="prefix_array_construction",
                        description=f"Prefix array built in loop: '{', '.join(prefix_names)}'",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.40,
                    )
                )
                evidence.append(
                    EvidenceItem(
                        type="prefix_accumulator",
                        description="Cumulative accumulation in loop body",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

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

    def _find_prefix_array_targets(self, body: list) -> Set[str]:
        """Find variable names that have subscript assignments in loop body."""
        names = set()
        for stmt in body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Subscript):
                        if isinstance(target.value, ast.Name):
                            names.add(target.value.id)
        return names

    def _find_append_to_list(self, body: list) -> bool:
        """Check if there's an .append() call in the loop body."""
        for stmt in ast.walk(ast.Module(body=body)):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Attribute) and stmt.func.attr == "append":
                    return True
        return False

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
        for stmt in body:
            yield stmt
            for subnode in ast.walk(stmt):
                yield subnode

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
                        if isinstance(subnode.value, ast.Name) and subnode.value.id not in running_vars:
                            return True
                    if isinstance(subnode, ast.BinOp) and isinstance(subnode.op, ast.Sub):
                        if isinstance(subnode.left, ast.Name) and subnode.left.id in running_vars:
                            return True
                    if isinstance(subnode, ast.Call):
                        if isinstance(subnode.func, ast.Attribute) and subnode.func.attr == "get":
                            return True
                        if isinstance(subnode.func, ast.Name) and subnode.func.id == "get":
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
