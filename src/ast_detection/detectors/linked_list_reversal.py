"""Detector for linked list reversal pattern.

Detects both iterative and recursive linked list reversal patterns.

Does NOT detect:
- Ordinary linked-list traversal without pointer rewiring.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class LinkedListReversalDetector(BaseDetector):
    pattern_id = "linked_list_reversal"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_iterative_reversal(ast_root, evidence)
        self._detect_recursive_reversal(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_recursive = any(e.type == "recursive_rewiring" for e in evidence)
        has_rewiring = any(e.type == "pointer_rewiring" for e in evidence)
        has_secondary = any(
            e.type in ("prev_curr_update", "reversal_variable_names")
            for e in evidence
        )
        detected = has_recursive or (has_rewiring and has_secondary)

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_iterative_reversal(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: while loop with linked-list pointer rewiring and shifting.

        Core pattern:
            prev = None
            curr = head
            while curr:
                nxt = curr.next
                curr.next = prev
                prev = curr
                curr = nxt
        """
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.While):
                continue

            # Look for pointer rewiring (curr.next = prev) inside the while loop body
            has_rewiring = False
            for child in ast.walk(ast.Module(body=node.body)):
                if isinstance(child, ast.Assign):
                    if len(child.targets) == 1:
                        target = child.targets[0]
                        if isinstance(target, ast.Attribute) and target.attr == "next":
                            if isinstance(target.value, ast.Name):
                                has_rewiring = True
                        if isinstance(target, (ast.Tuple, ast.List)) and isinstance(child.value, (ast.Tuple, ast.List)):
                            if len(target.elts) == len(child.value.elts):
                                for t, v in zip(target.elts, child.value.elts):
                                    if isinstance(t, ast.Attribute) and t.attr == "next":
                                        if isinstance(t.value, ast.Name):
                                            has_rewiring = True

            # If there's no pointer rewiring, we don't treat it as iterative reversal (to prevent false positives)
            if not has_rewiring:
                continue

            evidence.append(
                EvidenceItem(
                    type="pointer_rewiring",
                    description="Linked-list pointer rewiring (e.g., curr.next = prev) found in loop body",
                    location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                    weight=0.50,
                )
            )

            # Check for shifting pattern: prev = curr; curr = nxt
            shift_pairs = []
            for child in ast.walk(ast.Module(body=node.body)):
                if isinstance(child, ast.Assign):
                    if len(child.targets) == 1:
                        target = child.targets[0]
                        if isinstance(target, ast.Name) and isinstance(child.value, ast.Name):
                            shift_pairs.append((target.id, child.value.id))
                        if isinstance(target, (ast.Tuple, ast.List)) and isinstance(child.value, (ast.Tuple, ast.List)):
                            if len(target.elts) == len(child.value.elts):
                                for t, v in zip(target.elts, child.value.elts):
                                    if isinstance(t, ast.Name) and isinstance(v, ast.Name):
                                        shift_pairs.append((t.id, v.id))

            has_shift = False
            for p1 in shift_pairs:
                for p2 in shift_pairs:
                    if p1[1] == p2[0] and p1[0] != p2[1]:
                        has_shift = True
                        break
                if has_shift:
                    break

            if has_shift:
                evidence.append(
                    EvidenceItem(
                        type="prev_curr_update",
                        description="Pointer shifting updates (e.g., prev = curr; curr = next) found in loop body",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

            # Check for characteristic variable names
            reversal_names = {"prev", "previous", "curr", "current", "next_node", "next_temp", "nxt", "nxt_temp"}
            found_names = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Name):
                    name_lower = child.id.lower()
                    for r in reversal_names:
                        if r in name_lower:
                            found_names.add(child.id)

            if len(found_names) >= 2:
                evidence.append(
                    EvidenceItem(
                        type="reversal_variable_names",
                        description=f"Traditional linked list reversal variable names found: {sorted(list(found_names))}",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
                    )
                )

    def _detect_recursive_reversal(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: recursive linked-list reversal with recursive rewiring.

        Core pattern:
            p = reverseList(head.next)
            head.next.next = head
            head.next = None
        """
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.FunctionDef):
                continue

            # Look for recursive rewiring (head.next.next = head)
            has_recursive_rewiring = False
            base_var = ""
            for child in ast.walk(node):
                if isinstance(child, ast.Assign) and len(child.targets) == 1:
                    target = child.targets[0]
                    if isinstance(target, ast.Attribute) and target.attr == "next":
                        if isinstance(target.value, ast.Attribute) and target.value.attr == "next":
                            if isinstance(target.value.value, ast.Name):
                                b_var = target.value.value.id
                                if isinstance(child.value, ast.Name) and child.value.id == b_var:
                                    has_recursive_rewiring = True
                                    base_var = b_var
                                    break

            # If there's no recursive rewiring, we don't treat it as recursive reversal
            if not has_recursive_rewiring:
                continue

            evidence.append(
                EvidenceItem(
                    type="recursive_rewiring",
                    description=f"Recursive linked-list pointer rewiring (e.g., {base_var}.next.next = {base_var}) found",
                    location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                    weight=0.60,
                )
            )

            # Check for recursive call with next: reverseList(head.next)
            has_recursive_call = False
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                    if child.func.id == node.name:
                        for arg in child.args:
                            if isinstance(arg, ast.Attribute) and arg.attr == "next":
                                has_recursive_call = True
                                break
                        if has_recursive_call:
                            break

            if has_recursive_call:
                evidence.append(
                    EvidenceItem(
                        type="recursive_call_with_next",
                        description=f"Recursive call passing next node (e.g., {node.name}(node.next))",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.40,
                    )
                )

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
