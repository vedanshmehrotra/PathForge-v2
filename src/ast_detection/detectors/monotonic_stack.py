"""Detector for monotonic stack pattern.

Detects stack-based algorithms where elements are pushed and then popped
based on a monotonic invariant (comparison-driven popping). Characteristic
of next greater element, daily temperatures, stock span problems.

Does NOT trigger on ordinary stack usage (push/pop without comparison).
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class MonotonicStackDetector(BaseDetector):
    pattern_id = "monotonic_stack"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_monotonic_stack(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=confidence > 0.0,
        )

    def _detect_monotonic_stack(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: for loop with stack, push, and comparison-driven pop.

        Core pattern:
            stack = []
            for i in range(len(arr)):
                while stack and arr[stack[-1]] < arr[i]:
                    stack.pop()
                stack.append(i)
        """
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.For):
                continue

            stack_var = self._find_stack_initialized_before(ast_root, node)
            if stack_var is None:
                continue

            inner_while = self._find_inner_while(node.body)
            if inner_while is None:
                continue

            comparison_pop = self._find_comparison_driven_pop(inner_while, stack_var)
            if comparison_pop is None:
                continue

            has_push = self._find_stack_push(node.body, stack_var)
            has_pop = self._find_stack_pop(node.body, stack_var)

            if comparison_pop and has_push:
                evidence.append(
                    EvidenceItem(
                        type="monotonic_pop",
                        description=f"Comparison-driven pop from '{stack_var}' with {comparison_pop}",
                        location=f"{inner_while.lineno}:{inner_while.col_offset}" if hasattr(inner_while, "lineno") else None,
                        weight=0.40,
                    )
                )
                if has_push:
                    evidence.append(
                        EvidenceItem(
                            type="stack_push",
                            description=f"Push to stack '{stack_var}'",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )
                evidence.append(
                    EvidenceItem(
                        type="comparison_loop",
                        description=f"For loop with monotonic stack maintenance",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

    def _find_stack_initialized_before(self, root: ast.AST, target_for: ast.For) -> str | None:
        """Find a list variable initialized with [] or list() before the for loop."""
        for stmt in getattr(root, 'body', []):
            if stmt is target_for:
                break
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id != "self":
                        val = stmt.value
                        if isinstance(val, ast.List) and len(val.elts) == 0:
                            return target.id
                        if isinstance(val, ast.Call):
                            if isinstance(val.func, ast.Name) and val.func.id == "list" and len(val.args) == 0:
                                return target.id
            elif isinstance(stmt, ast.FunctionDef):
                result = self._find_stack_initialized_before(stmt, target_for)
                if result:
                    return result
        return None

    def _find_inner_while(self, body: list) -> ast.While | None:
        """Find a while loop inside the given body."""
        for stmt in body:
            if isinstance(stmt, ast.While):
                return stmt
            if isinstance(stmt, (ast.If, ast.For)):
                result = self._find_inner_while(stmt.body)
                if result:
                    return result
                if isinstance(stmt, ast.If):
                    result = self._find_inner_while(stmt.orelse)
                    if result:
                        return result
        return None

    def _find_comparison_driven_pop(self, while_node: ast.While, stack_var: str) -> str | None:
        """Check if the while loop has comparison-driven pop on the stack.

        Identifies: while stack and condition(arr[stack[-1]], arr[i]): stack.pop()

        Returns the comparison type (e.g., '<', '>', '<=', '>=') or None.
        """
        test = while_node.test
        has_stack_ref = False
        comparison_op = None

        if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
            for value_node in test.values:
                for sub in ast.walk(value_node):
                    if isinstance(sub, ast.Name) and sub.id == stack_var:
                        has_stack_ref = True
                if isinstance(value_node, ast.Compare):
                    for op in value_node.ops:
                        if isinstance(op, (ast.Lt, ast.Gt, ast.LtE, ast.GtE)):
                            comparison_op = type(op).__name__

        for sub in ast.walk(test):
            if isinstance(sub, ast.Name) and sub.id == stack_var:
                has_stack_ref = True
            if isinstance(sub, ast.Subscript):
                if isinstance(sub.value, ast.Name) and sub.value.id == stack_var:
                    if isinstance(sub.slice, ast.UnaryOp):
                        if isinstance(sub.slice.operand, ast.Constant):
                            has_stack_ref = True
                    if isinstance(sub.slice, ast.Constant):
                        has_stack_ref = True
                    if isinstance(sub.slice, ast.Call):
                        if isinstance(sub.slice.func, ast.Attribute) and sub.slice.func.attr in ("pop", "__getitem__"):
                            has_stack_ref = True

        has_pop = False
        for stmt in ast.walk(while_node):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Attribute):
                    if isinstance(stmt.func.value, ast.Name) and stmt.func.value.id == stack_var:
                        if stmt.func.attr == "pop":
                            has_pop = True

        if has_stack_ref and has_pop:
            return comparison_op or "__contains__"
        return None

    def _find_stack_push(self, body: list, stack_var: str) -> bool:
        """Check if there's an append (push) to the stack variable."""
        for stmt in ast.walk(ast.Module(body=body)):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Attribute):
                    if isinstance(stmt.func.value, ast.Name) and stmt.func.value.id == stack_var:
                        if stmt.func.attr == "append":
                            return True
        return False

    def _find_stack_pop(self, body: list, stack_var: str) -> bool:
        """Check if there's a pop from the stack variable."""
        for stmt in ast.walk(ast.Module(body=body)):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Attribute):
                    if isinstance(stmt.func.value, ast.Name) and stmt.func.value.id == stack_var:
                        if stmt.func.attr == "pop":
                            return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
