"""Detector for fast & slow pointers (Floyd's cycle detection) in linked lists.

Detects different-speed successor traversal on linked lists or a common
indexed functional graph (Floyd's Tortoise and Hare algorithm).

Does NOT detect:
- Ordinary array indices without successor-table traversal
- General linked-list traversal without differential advancement
- Cycle detection using hash sets (handled by hash_map_lookup)
"""

import ast
from src.ast_detection.python_structure import assignment_values
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class FastSlowPointersDetector(BaseDetector):
    pattern_id = "fast_slow_pointers"

    def detect(self, ast_root):
        evidence = []
        for loop in ast.walk(ast_root):
            if not isinstance(loop, ast.While):
                continue
            advancement = self._collect_advancements_robust(loop.body)
            pairs = [(a, b) for a in advancement for b in advancement
                     if advancement[a] == 1 and advancement[b] > 1]
            if not pairs:
                continue
            a, b = pairs[0]
            evidence.extend([
                EvidenceItem(type='floyd_traversal', description='Same-loop successor cursors advance at different speeds',
                             location=f'{loop.lineno}:{loop.col_offset}', weight=0.60),
                # Keep the legacy evidence key for response compatibility.
                EvidenceItem(type='pointer_names', description='Pointer identities are linked to one-hop and multi-hop updates; spelling is irrelevant',
                             location=f'{loop.lineno}:{loop.col_offset}', weight=0.20)])
            comparisons = [loop.test] + [s.test for s in loop.body if isinstance(s, ast.If)]
            if any(isinstance(test, ast.Compare) and len(test.ops) == 1
                   and isinstance(test.ops[0], (ast.Eq, ast.NotEq, ast.Is, ast.IsNot))
                   and isinstance(test.left, ast.Name) and isinstance(test.comparators[0], ast.Name)
                   and {test.left.id, test.comparators[0].id} == {a, b} for test in comparisons):
                evidence.append(EvidenceItem(type='cycle_check', description='The different-speed cursors are compared', weight=0.40))
        return DetectionResult(pattern_id=self.pattern_id, confidence=self._calculate_confidence(evidence),
                               evidence=evidence, detected=bool(evidence))


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

    def _collect_advancements_robust(self, body):
        hops_map = {}
        domains = {}
        invalid = set()
        for statement in body:
            for target, value in assignment_values(statement).items():
                base, hops = self._extract_next_chain(value)
                domain = 'next'
                if not hops:
                    current = value
                    collection = None
                    while (isinstance(current, ast.Subscript) and isinstance(current.value, ast.Name)
                           and (collection is None or collection == current.value.id)):
                        collection = current.value.id
                        hops += 1
                        current = current.slice
                    base = current.id if isinstance(current, ast.Name) else None
                    domain = collection
                if base == target and hops:
                    if target in domains and domains[target] != domain:
                        invalid.add(target)
                    hops_map[target] = hops_map.get(target, 0) + hops
                    domains[target] = domain
                else:
                    invalid.add(target)
        # Array-functional-graph Floyd and linked-list Floyd share a successor
        # relationship; unrelated successor containers must not be pooled.
        pairs = {a for a in hops_map for b in hops_map if a != b
                 and not {a, b} & invalid and domains[a] == domains[b] and hops_map[a] != hops_map[b]}
        return {key: value for key, value in hops_map.items() if key in pairs}


    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
