"""Detector for monotonic queue (deque) pattern.

Detects deque-based monotonic queue algorithms where elements are appended
and then popped (from either end) based on a monotonic invariant.
Characteristic of sliding window maximum/minimum problems.

Does NOT trigger on ordinary queue or list usage without comparison-driven
deque maintenance.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class MonotonicQueueDetector(BaseDetector):
    pattern_id = "monotonic_deque"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_monotonic_deque(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=confidence > 0.0,
        )

    def _detect_monotonic_deque(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: for loop with deque, comparison-driven pop, and popleft.

        Core pattern:
            from collections import deque
            dq = deque()
            for i in range(len(arr)):
                while dq and arr[dq[-1]] < arr[i]:
                    dq.pop()
                dq.append(i)
                if dq[0] < i - k + 1:
                    dq.popleft()
        """
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.For):
                continue

            deque_var = self._find_deque_initialized_before(ast_root, node)
            if deque_var is None:
                continue

            inner_while = self._find_inner_while(node.body)
            if inner_while is None:
                continue

            comparison_pop = self._find_comparison_driven_pop(inner_while, deque_var)
            if comparison_pop is None:
                continue

            has_append = self._find_deque_append(node.body, deque_var)
            has_popleft = self._find_popleft(node.body, deque_var)

            if comparison_pop and has_append:
                evidence.append(
                    EvidenceItem(
                        type="monotonic_pop",
                        description=f"Comparison-driven pop from deque '{deque_var}'",
                        location=f"{inner_while.lineno}:{inner_while.col_offset}" if hasattr(inner_while, "lineno") else None,
                        weight=0.35,
                    )
                )
                if has_append:
                    evidence.append(
                        EvidenceItem(
                            type="queue_append",
                            description=f"Append to deque '{deque_var}'",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.20,
                        )
                    )
                if has_popleft:
                    evidence.append(
                        EvidenceItem(
                            type="queue_popleft",
                            description=f"Popleft from deque '{deque_var}'",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.30,
                        )
                    )
                evidence.append(
                    EvidenceItem(
                        type="deque_creation",
                        description=f"Deque '{deque_var}' used in monotonic queue pattern",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
                    )
                )

    def _find_deque_initialized_before(self, root: ast.AST, target_for: ast.For) -> str | None:
        """Find a deque variable initialized before the for loop.

        Matches: dq = deque() or queue = deque()
        """
        for stmt in getattr(root, 'body', []):
            if stmt is target_for:
                break
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id != "self":
                        val = stmt.value
                        if isinstance(val, ast.Call):
                            if isinstance(val.func, ast.Name) and val.func.id == "deque" and len(val.args) <= 1:
                                return target.id
            elif isinstance(stmt, ast.FunctionDef):
                result = self._find_deque_initialized_before(stmt, target_for)
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

    def _find_comparison_driven_pop(self, while_node: ast.While, deque_var: str) -> str | None:
        """Check if the while loop has comparison-driven pop on the deque.

        Identifies: while dq and arr[dq[-1]] < arr[i]: dq.pop()

        Returns the comparison type or None.
        """
        has_deque_ref = False

        for sub in ast.walk(while_node.test):
            if isinstance(sub, ast.Name) and sub.id == deque_var:
                has_deque_ref = True
            if isinstance(sub, ast.Subscript):
                if isinstance(sub.value, ast.Name) and sub.value.id == deque_var:
                    has_deque_ref = True

        has_pop = False
        for stmt in ast.walk(while_node):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Attribute):
                    if isinstance(stmt.func.value, ast.Name) and stmt.func.value.id == deque_var:
                        if stmt.func.attr in ("pop", "popleft"):
                            has_pop = True

        if has_deque_ref and has_pop:
            return "comparison_pop"
        return None

    def _find_deque_append(self, body: list, deque_var: str) -> bool:
        """Check if there's an append to the deque variable."""
        for stmt in ast.walk(ast.Module(body=body)):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Attribute):
                    if isinstance(stmt.func.value, ast.Name) and stmt.func.value.id == deque_var:
                        if stmt.func.attr == "append":
                            return True
        return False

    def _find_popleft(self, body: list, deque_var: str) -> bool:
        """Check if there's a popleft from the deque variable."""
        for stmt in ast.walk(ast.Module(body=body)):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Attribute):
                    if isinstance(stmt.func.value, ast.Name) and stmt.func.value.id == deque_var:
                        if stmt.func.attr == "popleft":
                            return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
