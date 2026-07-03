"""Detector for two pointers opposite direction pattern.

Detects left/right converging pointer patterns where one pointer
starts at the beginning and the other at the end, moving toward
each other based on comparisons.

Does NOT detect same-direction (slow/fast) two-pointer patterns.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class TwoPointersOppositeDetector(BaseDetector):
    pattern_id = "two_pointers_opposite"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_convergence_loop(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=confidence > 0.0,
        )

    def _detect_convergence_loop(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: while loop with bidirectional pointer convergence.

        Core pattern:
            left = 0
            right = len(arr) - 1
            while left < right:
                if condition:
                    left += 1
                else:
                    right -= 1
        """
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.While):
                continue

            condition = node.test
            if not isinstance(condition, ast.Compare):
                continue

            if len(condition.ops) != 1:
                continue

            if not isinstance(condition.ops[0], (ast.Lt, ast.LtE)):
                continue

            left_name = None
            right_name = None
            if isinstance(condition.left, ast.Name) and isinstance(condition.comparators[0], ast.Name):
                left_name = condition.left.id
                right_name = condition.comparators[0].id
            elif isinstance(condition.left, ast.Name) and isinstance(condition.comparators[0], ast.Call):
                left_name = condition.left.id
            else:
                continue

            if left_name is None:
                continue

            body_increments = self._collect_opposite_increments(node.body, evidence)
            if not body_increments:
                continue

            left_increment = body_increments.get("left")
            right_decrement = body_increments.get("right")

            has_increment = left_increment == 1
            has_decrement = right_decrement == -1

            if has_increment and has_decrement:
                if left_name:
                    evidence.append(
                        EvidenceItem(
                            type="left_pointer_increment",
                            description=f"Left pointer '{left_name}' increments toward center",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )
                if right_name:
                    evidence.append(
                        EvidenceItem(
                            type="right_pointer_decrement",
                            description=f"Right pointer '{right_name}' decrements toward center",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )
                evidence.append(
                    EvidenceItem(
                        type="convergence_loop",
                        description=f"While loop converging {left_name} < {right_name}",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.40,
                    )
                )

    def _collect_opposite_increments(self, body: list, evidence: list) -> dict:
        """Collect pointer increment directions from loop body.

        Returns dict with optional 'left' and 'right' keys mapping to step values.
        Looks for +=1 and -=1 patterns, typically in if/elif/else branches.
        """
        result = {}
        for stmt in body:
            if isinstance(stmt, ast.If):
                for branch in self._flatten_branches(stmt):
                    for s in branch:
                        if isinstance(s, ast.AugAssign):
                            if isinstance(s.target, ast.Name):
                                if isinstance(s.op, ast.Add) and isinstance(s.value, ast.Constant) and s.value.value == 1:
                                    result["left"] = 1
                                elif isinstance(s.op, ast.Sub) and isinstance(s.value, ast.Constant) and s.value.value == 1:
                                    result["right"] = -1
            if isinstance(stmt, ast.AugAssign):
                if isinstance(stmt.target, ast.Name):
                    if isinstance(stmt.op, ast.Add) and isinstance(stmt.value, ast.Constant) and stmt.value.value == 1:
                        result["left"] = 1
                    elif isinstance(stmt.op, ast.Sub) and isinstance(stmt.value, ast.Constant) and stmt.value.value == 1:
                        result["right"] = -1
        return result

    def _flatten_branches(self, if_node: ast.If) -> list:
        """Flatten if/elif/else branches into a list of body lists.

        Handles nested elif chains by recursively processing orelse.
        """
        branches = [if_node.body]
        for stmt in if_node.orelse:
            if isinstance(stmt, ast.If):
                branches.extend(self._flatten_branches(stmt))
            else:
                branches.append(if_node.orelse)
                break
        return branches

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
