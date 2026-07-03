"""Detector for two pointers same direction pattern.

Detects slow/fast pointer or same-direction two-pointer traversals
where both pointers move forward but at different speeds or offsets.

Does NOT detect opposite direction (left/right converging) two-pointer patterns.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class TwoPointersSameDetector(BaseDetector):
    pattern_id = "two_pointers_same"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_slow_fast_differential(ast_root, evidence)
        self._detect_offset_pointer_loop(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=confidence > 0.0,
        )

    def _detect_slow_fast_differential(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: while loop where two or more variables are incremented by different step sizes.

        Matches:
            while fast < len(arr):
                slow += 1
                fast += 2
        """
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.While):
                continue

            increments = self._collect_increments_in_body(node.body)
            if len(increments) < 2:
                continue

            step_values = set()
            for steps in increments.values():
                for s in steps:
                    step_values.add(s)

            if len(step_values) < 2:
                continue

            has_self_reference = False
            for var_name, steps in increments.items():
                for step in steps:
                    if step in (1, -1):
                        has_self_reference = True
                        break
                if has_self_reference:
                    break

            if has_self_reference:
                evidence.append(
                    EvidenceItem(
                        type="slow_fast_differential",
                        description=f"While loop with {len(increments)} pointer variables and differential speed ({step_values})",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.40,
                    )
                )

    def _detect_offset_pointer_loop(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: while loop with offset pointer assignments (linked list style).

        Matches:
            slow = head
            fast = head.next
            while fast and fast.next:
                slow = slow.next
                fast = fast.next.next
        """
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.While):
                continue

            body_assigns = self._collect_assignments(node.body)
            while_body_names = set()
            for assign in body_assigns:
                if isinstance(assign, ast.Assign):
                    for t in assign.targets:
                        if isinstance(t, ast.Name):
                            while_body_names.add(t.id)

            condition_names = set()
            for cond_node in ast.walk(node.test):
                if isinstance(cond_node, ast.Name):
                    condition_names.add(cond_node.id)

            overlapping = while_body_names & condition_names
            if len(overlapping) >= 1 and len(while_body_names) >= 2:
                has_next_ref = False
                for stmt in ast.walk(node):
                    if isinstance(stmt, ast.Attribute) and stmt.attr == "next":
                        has_next_ref = True
                        break

                if has_next_ref or not evidence:
                    evidence.append(
                        EvidenceItem(
                            type="offset_pointer_assignment",
                            description=f"Loop with {len(while_body_names)} pointer variables; {len(overlapping)} in condition",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.30,
                        )
                    )

    def _collect_increments_in_body(self, body: list) -> dict:
        """Collect variable names and their increment values from AugAssign (+=) nodes.

        Returns dict mapping variable_name -> set(step_values)
        """
        increments = {}
        for stmt in body:
            if isinstance(stmt, ast.AugAssign):
                if isinstance(stmt.op, ast.Add) and isinstance(stmt.target, ast.Name):
                    if isinstance(stmt.value, ast.Constant):
                        increments.setdefault(stmt.target.id, set()).add(stmt.value.value)
                    elif isinstance(stmt.value, ast.UnaryOp) and isinstance(stmt.value.op, ast.USub):
                        if isinstance(stmt.value.operand, ast.Constant):
                            increments.setdefault(stmt.target.id, set()).add(-stmt.value.operand.value)
            elif isinstance(stmt, ast.For):
                inc = self._collect_increments_in_body(stmt.body)
                self._merge(increments, inc)
            elif isinstance(stmt, ast.While):
                inc = self._collect_increments_in_body(stmt.body)
                self._merge(increments, inc)
            elif isinstance(stmt, ast.If):
                inc = self._collect_increments_in_body(stmt.body)
                self._merge(increments, inc)
                inc = self._collect_increments_in_body(stmt.orelse)
                self._merge(increments, inc)
        return increments

    def _collect_assignments(self, body: list) -> list:
        """Collect all assignment statements from a body recursively."""
        assigns = []
        for stmt in body:
            if isinstance(stmt, ast.Assign):
                assigns.append(stmt)
            elif isinstance(stmt, (ast.For, ast.While, ast.If)):
                assigns.extend(self._collect_assignments(stmt.body))
                if isinstance(stmt, ast.If):
                    assigns.extend(self._collect_assignments(stmt.orelse))
        return assigns

    @staticmethod
    def _merge(target: dict, source: dict) -> None:
        for key, values in source.items():
            if key not in target:
                target[key] = set()
            target[key].update(values)

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
