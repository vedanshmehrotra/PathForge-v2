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
        self._detect_pointer_names(ast_root, evidence)
        self._detect_floyd_traversal(ast_root, evidence)
        self._detect_cycle_check(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_core_signal = any(
            e.type in ("floyd_traversal", "cycle_check") for e in evidence
        )

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=has_core_signal,
        )

    def _detect_pointer_names(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: presence of typical fast/slow pointer names.

        Matches variable names like slow, fast, tortoise, hare, slow_ptr, fast_ptr.
        """
        detected_names = set()
        target_names = {"slow", "fast", "tortoise", "hare", "slow_ptr", "fast_ptr"}
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Name):
                name_lower = node.id.lower()
                for t in target_names:
                    if t in name_lower:
                        detected_names.add(node.id)

        if len(detected_names) >= 2:
            evidence.append(
                EvidenceItem(
                    type="pointer_names",
                    description=f"Traditional fast/slow pointer variable names found: {sorted(list(detected_names))}",
                    weight=0.20,
                )
            )

    def _detect_floyd_traversal(self, ast_root: ast.AST, evidence: list) -> None:
        """Signal: while loop with linked-list slow/fast pointer advancement.

        Core pattern:
            slow = head
            fast = head
            while fast and fast.next:
                slow = slow.next
                fast = fast.next.next

        Requires .next attribute in the loop body or condition (linked-list context).
        """
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.While):
                continue

            if not self._has_next_in_loop(node):
                continue

            advancement = self._collect_advancements_robust(node.body)
            if len(advancement) < 2:
                continue

            step_counts = set(advancement.values())
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
        target_names = {"slow", "fast", "tortoise", "hare", "slow_ptr", "fast_ptr"}
        pointer_pairs = set()
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.While):
                continue

            advancement = self._collect_advancements_robust(node.body)
            pointer_names = set(advancement.keys())

            for child in ast.walk(node):
                if isinstance(child, ast.Name):
                    name_lower = child.id.lower()
                    for t in target_names:
                        if t in name_lower:
                            pointer_names.add(child.id)

            if len(pointer_names) < 2:
                continue

            # 1. Search in while condition
            if isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
                if isinstance(node.test.ops[0], (ast.Eq, ast.Is, ast.IsNot, ast.NotEq)):
                    left = self._extract_name(node.test.left)
                    right = self._extract_name(node.test.comparators[0])
                    if left in pointer_names and right in pointer_names:
                        pointer_pairs.add((left, right))

            # 2. Search in loop body
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

    def _has_next_in_loop(self, node: ast.While) -> bool:
        """Check if the while loop (condition or body) contains a .next attribute reference."""
        for child in ast.walk(node):
            if isinstance(child, ast.Attribute) and child.attr == "next":
                return True
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

    def _collect_advancements_robust(self, body: list) -> dict:
        """Collect variable names and their total next-advancement hops in the loop.

        Returns a dict mapping variable_name to total hops.
        """
        hops_map = {}
        # Walk all assignments in the body
        for node in ast.walk(ast.Module(body=body)):
            if isinstance(node, ast.Assign):
                if len(node.targets) == 1:
                    target = node.targets[0]
                    if isinstance(target, ast.Name):
                        base_name, hops = self._extract_next_chain(node.value)
                        if base_name == target.id and hops > 0:
                            hops_map[target.id] = hops_map.get(target.id, 0) + hops
                    elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(node.value, (ast.Tuple, ast.List)):
                        if len(target.elts) == len(node.value.elts):
                            for t, v in zip(target.elts, node.value.elts):
                                if isinstance(t, ast.Name):
                                    base_name, hops = self._extract_next_chain(v)
                                    if base_name == t.id and hops > 0:
                                        hops_map[t.id] = hops_map.get(t.id, 0) + hops
        return hops_map

    def _extract_name(self, node: ast.AST) -> str:
        """Extract variable name from an expression node, or empty string."""
        if isinstance(node, ast.Name):
            return node.id
        return ""

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
