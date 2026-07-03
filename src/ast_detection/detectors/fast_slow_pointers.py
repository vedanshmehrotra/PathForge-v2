"""Detector for fast & slow pointers (Floyd's cycle detection) in linked lists.

Detects Floyd's Tortoise and Hare algorithm structural patterns where
two pointers traverse a linked list at different speeds to detect cycles.

Does NOT detect:
- Array-based two-pointer algorithms (handled by two_pointers_same)
- General linked-list traversal without differential advancement
- Cycle detection using hash sets (handled by hash_map_lookup)
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class FastSlowPointersDetector(BaseDetector):
    pattern_id = "fast_slow_pointers"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_floyd_traversal(ast_root, evidence)
        self._detect_cycle_check(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=confidence > 0.0,
        )

    def _detect_floyd_traversal(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: while loop with linked-list slow/fast pointer advancement.

        Core pattern:
            slow = head
            fast = head
            while fast and fast.next:
                slow = slow.next
                fast = fast.next.next

        Requires .next attribute in the while condition (linked-list context).
        """
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.While):
                continue

            if not self._has_next_in_condition(node.test):
                continue

            advancement = self._collect_next_advancements(node.body)
            if len(advancement) < 2:
                continue

            step_counts = set()
            for var, steps in advancement.items():
                for s in steps:
                    step_counts.add(s)

            if len(step_counts) < 2:
                continue

            evidence.append(
                EvidenceItem(
                    type="floyd_traversal",
                    description=f"Linked-list traversal with {len(advancement)} pointers at differential speeds ({step_counts})",
                    location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                    weight=0.60,
                )
            )

    def _detect_cycle_check(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: equality comparison of slow and fast pointers indicating cycle detection.

        Matches:
            if slow == fast:
                return True   (cycle found)
        or equivalent comparison between pointer variables used in advancement.
        """
        pointer_pairs = set()
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.While):
                continue

            if not self._has_next_in_condition(node.test):
                continue

            advancement = self._collect_next_advancements(node.body)
            pointer_names = set(advancement.keys())
            if len(pointer_names) < 2:
                continue

            for stmt in ast.walk(ast.Module(body=node.body)):
                if isinstance(stmt, ast.If):
                    test = stmt.test
                    if isinstance(test, ast.Compare) and len(test.ops) == 1:
                        if isinstance(test.ops[0], (ast.Eq, ast.Is, ast.IsNot, ast.NotEq)):
                            left = self._extract_name(test.left)
                            right = self._extract_name(test.comparators[0])
                            if left in pointer_names and right in pointer_names:
                                pointer_pairs.add((left, right))

        for pair in pointer_pairs:
            evidence.append(
                EvidenceItem(
                    type="cycle_check",
                    description=f"Cycle detection comparison: {pair[0]} == {pair[1]}",
                    weight=0.40,
                )
            )

    def _has_next_in_condition(self, test: ast.AST) -> bool:
        """Check if the while condition contains a .next attribute reference or simple pointer check."""
        for node in ast.walk(test):
            if isinstance(node, ast.Attribute) and node.attr == "next":
                return True
            # In some cases, condition might just be `while fast:` with body checking `fast.next`
            # or simply using names that are traversed. But .next in condition is the primary signal.
        return False

    def _extract_next_chain(self, node: ast.AST):
        """If node is a chain of .next attributes (like fast.next.next),
        returns (base_name, hop_count). Otherwise returns (None, 0).
        """
        current = node
        hops = 0
        while isinstance(current, ast.Attribute) and current.attr == "next":
            hops += 1
            current = current.value
        if isinstance(current, ast.Name):
            return current.id, hops
        return None, 0

    def _collect_next_advancements(self, body: list) -> dict:
        """Collect variable names and their .next chain lengths (step counts).

        Returns dict mapping variable_name -> set(step_counts)
        where step_count is the number of .next hops (1 for .next, 2 for .next.next).
        """
        advancements = {}
        for stmt in body:
            if isinstance(stmt, ast.Assign):
                if len(stmt.targets) == 1:
                    target = stmt.targets[0]
                    if isinstance(target, ast.Name):
                        base_name, hops = self._extract_next_chain(stmt.value)
                        if base_name == target.id and hops > 0:
                            advancements.setdefault(target.id, set()).add(hops)
                    elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(stmt.value, (ast.Tuple, ast.List)):
                        if len(target.elts) == len(stmt.value.elts):
                            for t, v in zip(target.elts, stmt.value.elts):
                                if isinstance(t, ast.Name):
                                    base_name, hops = self._extract_next_chain(v)
                                    if base_name == t.id and hops > 0:
                                        advancements.setdefault(t.id, set()).add(hops)
            elif hasattr(stmt, "body") and isinstance(stmt.body, list):
                inc = self._collect_next_advancements(stmt.body)
                self._merge(advancements, inc)
                if hasattr(stmt, "orelse") and isinstance(stmt.orelse, list):
                    inc = self._collect_next_advancements(stmt.orelse)
                    self._merge(advancements, inc)
                if hasattr(stmt, "finalbody") and isinstance(stmt.finalbody, list):
                    inc = self._collect_next_advancements(stmt.finalbody)
                    self._merge(advancements, inc)
                if hasattr(stmt, "handlers") and isinstance(stmt.handlers, list):
                    for handler in stmt.handlers:
                        if hasattr(handler, "body") and isinstance(handler.body, list):
                            inc = self._collect_next_advancements(handler.body)
                            self._merge(advancements, inc)
        return advancements

    def _extract_name(self, node: ast.AST) -> str:
        """Extract variable name from an expression node, or empty string."""
        if isinstance(node, ast.Name):
            return node.id
        return ""

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
