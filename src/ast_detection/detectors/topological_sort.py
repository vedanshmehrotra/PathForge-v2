"""Detector for topological sort (Kahn's algorithm).

Detects graph topological sorting using indegree tracking and queue-based
processing. Characteristic of course schedule, dependency resolution,
and build-order problems.

Does NOT detect:
- Ordinary BFS/DFS without indegree tracking
- DFS-based topological sort without the three-state visited pattern
- Simple graph traversal without dependency resolution
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class TopologicalSortDetector(BaseDetector):
    pattern_id = "topological_sort"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_kahn_algorithm(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_indegree = any(e.type in ("indegree_array", "indegree_decrement", "indegree_increment") for e in evidence)
        has_queue_processing = any(e.type == "zero_indegree_queue" for e in evidence)
        has_enqueue = any(e.type == "conditional_enqueue" for e in evidence)

        detected = (has_indegree and has_queue_processing) or (has_indegree and has_enqueue)

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_kahn_algorithm(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if not isinstance(node, (ast.FunctionDef, ast.Module)):
                continue

            has_indegree = self._find_indegree_array(node)
            has_indegree_increment = self._find_indegree_increment(node)
            has_indegree_decrement = self._find_indegree_decrement(node)
            has_zero_indegree_queue = self._find_zero_indegree_queue(node)
            has_conditional_enqueue = self._find_conditional_enqueue(node)

            if not (has_indegree or has_indegree_increment or has_indegree_decrement):
                continue

            if has_indegree:
                evidence.append(
                    EvidenceItem(
                        type="indegree_array",
                        description="Indegree array creation for dependency tracking",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

            if has_indegree_increment:
                evidence.append(
                    EvidenceItem(
                        type="indegree_increment",
                        description="Indegree increment in edge-processing loop",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

            if has_indegree_decrement:
                evidence.append(
                    EvidenceItem(
                        type="indegree_decrement",
                        description="Indegree decrement when processing dependencies",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

            if has_zero_indegree_queue:
                evidence.append(
                    EvidenceItem(
                        type="zero_indegree_queue",
                        description="Queue initialized with zero-indegree nodes",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

            if has_conditional_enqueue:
                evidence.append(
                    EvidenceItem(
                        type="conditional_enqueue",
                        description="Conditional enqueue when indegree reaches zero",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

    def _find_indegree_array(self, node: ast.AST) -> bool:
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        name = target.id.lower()
                        if "indeg" in name or "in_degree" in name or "degree" in name:
                            val = child.value
                            if isinstance(val, ast.BinOp) and isinstance(val.op, ast.Mult):
                                if isinstance(val.left, ast.List) or isinstance(val.right, ast.List):
                                    return True
                                if isinstance(val.left, ast.Constant) and val.left.value == 0:
                                    return True
                                if isinstance(val.right, ast.Constant) and val.right.value == 0:
                                    return True
                            if isinstance(val, ast.ListComp):
                                return True
                            if isinstance(val, ast.DictComp):
                                return True
                            if isinstance(val, ast.Call):
                                if isinstance(val.func, ast.Name) and val.func.id == "list":
                                    return True
        return False

    def _find_indegree_increment(self, node: ast.AST) -> bool:
        for child in ast.walk(node):
            if isinstance(child, ast.AugAssign):
                if isinstance(child.target, ast.Subscript):
                    if isinstance(child.target.value, ast.Name):
                        name = child.target.value.id.lower()
                        if "indeg" in name or "degree" in name:
                            if isinstance(child.op, ast.Add):
                                if isinstance(child.value, ast.Constant) and child.value.value == 1:
                                    return True
                                if isinstance(child.value, ast.Name):
                                    return True
            if isinstance(child, ast.Assign):
                if len(child.targets) == 1 and isinstance(child.targets[0], ast.Subscript):
                    if isinstance(child.targets[0].value, ast.Name):
                        name = child.targets[0].value.id.lower()
                        if "indeg" in name or "degree" in name:
                            if isinstance(child.value, ast.BinOp) and isinstance(child.value.op, ast.Add):
                                return True
        return False

    def _find_indegree_decrement(self, node: ast.AST) -> bool:
        for child in ast.walk(node):
            if isinstance(child, ast.AugAssign):
                if isinstance(child.target, ast.Subscript):
                    if isinstance(child.target.value, ast.Name):
                        name = child.target.value.id.lower()
                        if "indeg" in name or "degree" in name:
                            if isinstance(child.op, ast.Sub):
                                if isinstance(child.value, ast.Constant) and child.value.value == 1:
                                    return True
            if isinstance(child, ast.Assign):
                if len(child.targets) == 1 and isinstance(child.targets[0], ast.Subscript):
                    if isinstance(child.targets[0].value, ast.Name):
                        name = child.targets[0].value.id.lower()
                        if "indeg" in name or "degree" in name:
                            if isinstance(child.value, ast.BinOp) and isinstance(child.value.op, ast.Sub):
                                return True
        return False

    def _find_zero_indegree_queue(self, node: ast.AST) -> bool:
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        val = child.value
                        result = self._check_queue_value(val)
                        if result:
                            return result
        return False

    def _check_queue_value(self, val: ast.AST) -> bool:
        if isinstance(val, ast.ListComp):
            if self._has_indegree_zero_in_comprehension(val):
                return True
        if isinstance(val, ast.List):
            for elt in val.elts:
                if isinstance(elt, ast.IfExp) and self._has_indegree_zero_in_ifexp(elt):
                    return True
        if isinstance(val, ast.Call):
            if isinstance(val.func, ast.Name) and val.func.id == "deque":
                for arg in val.args:
                    if self._check_queue_value(arg):
                        return True
        return False

    def _has_indegree_zero_in_comprehension(self, comp: ast.ListComp) -> bool:
        for gen in comp.generators:
            for if_clause in gen.ifs:
                if self._is_indegree_zero_check(if_clause):
                    return True
        return False

    def _is_indegree_zero_check(self, test: ast.AST) -> bool:
        if isinstance(test, ast.Compare) and len(test.ops) == 1:
            if isinstance(test.ops[0], (ast.Eq, ast.Is)):
                for side in (test.left, test.comparators[0]):
                    if isinstance(side, ast.Subscript):
                        if isinstance(side.value, ast.Name):
                            name = side.value.id.lower()
                            if "indeg" in name or "degree" in name:
                                other = test.comparators[0] if side is test.left else test.left
                                if isinstance(other, ast.Constant) and other.value == 0:
                                    return True
        return False

    def _has_indegree_zero_in_ifexp(self, ifexp: ast.IfExp) -> bool:
        return self._is_indegree_zero_check(ifexp.test)

    def _find_conditional_enqueue(self, node: ast.AST) -> bool:
        for child in ast.walk(node):
            if isinstance(child, ast.If):
                if self._is_indegree_zero_check(child.test):
                    for stmt in child.body:
                        if isinstance(stmt, ast.Expr):
                            if isinstance(stmt.value, ast.Call):
                                if isinstance(stmt.value.func, ast.Attribute):
                                    if stmt.value.func.attr in ("append", "extend"):
                                        return True
                        if isinstance(stmt, ast.Call):
                            if isinstance(stmt.func, ast.Attribute):
                                if stmt.func.attr in ("append", "extend"):
                                    return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
