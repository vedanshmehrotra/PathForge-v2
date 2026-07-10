"""Detector for sliding window variable size pattern.

Detects variable-size sliding window where the window expands
and shrinks dynamically based on a condition, typically used
for substring problems, longest/shortest subarray problems.

Does NOT detect fixed-size sliding window patterns.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class SlidingWindowVariableDetector(BaseDetector):
    pattern_id = "sliding_window_variable"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_variable_window_loop(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=confidence > 0.0,
        )

    def _detect_variable_window_loop(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: for loop with dynamic window management.

        Detects two variants:
        1. While-loop based: for loop with inner while that shrinks window
        2. If-based: for loop with conditional left pointer reassignment

        Core patterns:
            # While-based (min_window, longest_repeating):
            left = 0
            for right in range(len(arr)):
                window[arr[right]] = window.get(arr[right], 0) + 1
                while condition:
                    window[arr[left]] -= 1
                    left += 1

            # If-based (longest_substring):
            left = 0
            for right in range(len(s)):
                if s[right] in char_set:
                    left = max(left, char_set[s[right]] + 1)
                char_set[s[right]] = right
        """
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.For):
                continue

            right_var = None
            if isinstance(node.target, ast.Name):
                right_var = node.target.id
            elif isinstance(node.target, ast.Tuple):
                if node.target.elts and isinstance(node.target.elts[0], ast.Name):
                    right_var = node.target.elts[0].id

            if right_var is None:
                continue

            left_var = self._find_left_ptr_initialized_before(ast_root, node)
            if left_var is None:
                continue

            inner_while = self._find_inner_while(node.body)
            has_window_assign = self._find_window_assign(node.body, left_var)

            if inner_while and self._has_left_increment(inner_while, left_var):
                evidence.append(
                    EvidenceItem(
                        type="window_shrink_variable",
                        description=f"Variable window shrink via '{left_var}++' in inner while loop",
                        location=f"{inner_while.lineno}:{inner_while.col_offset}" if hasattr(inner_while, "lineno") else None,
                        weight=0.40,
                    )
                )
                evidence.append(
                    EvidenceItem(
                        type="window_expand",
                        description=f"Window expands via right pointer '{right_var}'",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
                    )
                )

                has_validity_check = self._find_validity_condition(inner_while)
                if has_validity_check:
                    evidence.append(
                        EvidenceItem(
                            type="window_validity_check",
                            description="Window validity condition in while loop",
                            location=f"{inner_while.lineno}:{inner_while.col_offset}" if hasattr(inner_while, "lineno") else None,
                            weight=0.30,
                        )
                    )
            elif has_window_assign and self._is_index_based_loop(node):
                evidence.append(
                    EvidenceItem(
                        type="window_expand",
                        description=f"Window expands via right pointer '{right_var}'",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
                    )
                )
                evidence.append(
                    EvidenceItem(
                        type="window_shrink_variable",
                        description=f"Variable window shrink via assignment to '{left_var}'",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.35,
                    )
                )

    def _find_left_ptr_initialized_before(self, root: ast.AST, target_for: ast.For) -> str | None:
        """Find left pointer variable name initialized to 0 before the for loop."""
        for stmt in getattr(root, 'body', []):
            if stmt is target_for:
                break
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id != "self":
                        val = stmt.value
                        if isinstance(val, ast.Constant) and val.value == 0:
                            return target.id
            elif isinstance(stmt, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                result = self._find_left_ptr_initialized_before(stmt, target_for)
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
        return None

    def _has_left_increment(self, while_node: ast.While, left_var: str) -> bool:
        """Check if the while loop body increments the left pointer."""
        for s in ast.walk(while_node):
            if isinstance(s, ast.AugAssign):
                if isinstance(s.target, ast.Name) and s.target.id == left_var:
                    if isinstance(s.op, ast.Add) and isinstance(s.value, ast.Constant) and s.value.value == 1:
                        return True
        return False

    def _find_window_assign(self, body: list, left_var: str) -> bool:
        """Check if the left pointer is updated via assignment in the loop body.

        Matches: left = max(left, ...) or left = ...
        """
        for stmt in body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == left_var:
                        return True
            if isinstance(stmt, ast.If):
                if self._find_window_assign(stmt.body, left_var):
                    return True
                if self._find_window_assign(stmt.orelse, left_var):
                    return True
        return False

    def _find_validity_condition(self, while_node: ast.While) -> bool:
        """Check if the while condition relates to window validity."""
        test = while_node.test
        for subnode in ast.walk(test):
            if isinstance(subnode, ast.Call):
                if isinstance(subnode.func, ast.Attribute):
                    if subnode.func.attr in ("get", "__getitem__", "count"):
                        return True
                elif isinstance(subnode.func, ast.Name) and subnode.func.id in ("len", "sum"):
                    return True
            if isinstance(subnode, ast.Compare):
                for comparator in subnode.comparators:
                    for inner in ast.walk(comparator):
                        if isinstance(inner, ast.Name) and inner.id not in ("left", "right"):
                            return True
        return False

    def _is_index_based_loop(self, node: ast.For) -> bool:
        """Check if the for loop iterates over indices (range/len/enumerate) not values."""
        if isinstance(node.target, ast.Tuple):
            return True
        if isinstance(node.iter, ast.Call):
            if isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                return True
            if isinstance(node.iter.func, ast.Attribute) and node.iter.func.attr == "keys":
                return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
