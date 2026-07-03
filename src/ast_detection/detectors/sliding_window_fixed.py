"""Detector for sliding window fixed size pattern.

Detects fixed-size window sliding over a sequence where a window
of constant size k advances element by element, maintaining window
state as it moves.

Does NOT detect variable-size sliding window patterns.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class SlidingWindowFixedDetector(BaseDetector):
    pattern_id = "sliding_window_fixed"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_fixed_window_loop(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=confidence > 0.0,
        )

    def _detect_fixed_window_loop(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: for loop with window size boundary check and removal pattern.

        Core pattern:
            for right in range(len(arr)):
                window_sum += arr[right]
                if right >= k - 1:
                    result.append(window_sum)
                    window_sum -= arr[left]
                    left += 1
        """
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.For):
                continue

            window_var = None
            if isinstance(node.target, ast.Name):
                window_var = node.target.id

            if window_var is None:
                continue

            bound_check = self._find_window_bound_check(node.body, window_var)
            if bound_check is None:
                continue

            if isinstance(bound_check, ast.If):
                bound_test = bound_check.test
                right_ge_check = None
                if isinstance(bound_test, ast.Compare):
                    has_window_var_left = isinstance(bound_test.left, ast.Name) and bound_test.left.id == window_var
                    has_window_var_in_comparators = False
                    for comp in bound_test.comparators:
                        found = self._contains_name(comp, window_var)
                        if found:
                            has_window_var_in_comparators = True
                            break
                    if has_window_var_left or has_window_var_in_comparators:
                        right_ge_check = bound_test

                if not right_ge_check:
                    continue

                has_window_shrink = False
                has_left_increment = False
                for s in bound_check.body:
                    if isinstance(s, ast.AugAssign):
                        target_name = None
                        if isinstance(s.target, ast.Name):
                            target_name = s.target.id
                        elif isinstance(s.target, ast.Subscript):
                            if isinstance(s.target.value, ast.Name):
                                target_name = s.target.value.id
                        if target_name:
                            if isinstance(s.op, ast.Sub):
                                has_window_shrink = True
                            if isinstance(s.op, ast.Add) and isinstance(s.value, ast.Constant) and s.value.value == 1:
                                if target_name != window_var:
                                    has_left_increment = True

                if has_window_shrink:
                    evidence.append(
                        EvidenceItem(
                            type="window_size_check",
                            description=f"Fixed window boundary check involving '{window_var}'",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.30,
                        )
                    )
                    evidence.append(
                        EvidenceItem(
                            type="window_expand",
                            description=f"Window expansion via '{window_var}' advancing",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.20,
                        )
                    )

                    shrink_desc_parts = []
                    if has_window_shrink:
                        shrink_desc_parts.append("element removal")
                    if has_left_increment:
                        shrink_desc_parts.append("left pointer advancement")
                    if shrink_desc_parts:
                        evidence.append(
                            EvidenceItem(
                                type="window_shrink_fixed",
                                description=f"Fixed window maintenance: {' and '.join(shrink_desc_parts)}",
                                location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                                weight=0.35,
                            )
                        )

    def _find_window_bound_check(self, body: list, window_var: str):
        """Find the if statement that checks if window reached full size."""
        for stmt in body:
            if isinstance(stmt, ast.If):
                return stmt
            if isinstance(stmt, ast.For):
                result = self._find_window_bound_check(stmt.body, window_var)
                if result:
                    return result
        return None

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
