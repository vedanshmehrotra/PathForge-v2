"""Detector for Union-Find (Disjoint Set Union) data structure.

Detects Union-Find implementations with parent array, find operations with
path compression, and union operations with optional rank/size optimization.

Does NOT detect:
- Ordinary tree traversals or graph traversals
- Non-DSU parent/child relationships in unrelated data structures
- Simple array operations without path compression or union logic
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class UnionFindDetector(BaseDetector):
    pattern_id = "union_find"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_union_find(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_parent_array = any(e.type == "parent_array" for e in evidence)
        has_find_operation = any(e.type in ("find_recursive", "find_iterative") for e in evidence)
        has_union_operation = any(e.type == "union_operation" for e in evidence)

        detected = has_parent_array and (has_find_operation or has_union_operation)

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_union_find(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.ClassDef):
                continue

            has_parent_array = self._find_parent_array_in_class(node)
            if not has_parent_array:
                continue

            has_find_recursive = self._find_find_recursive_in_class(node)
            has_find_iterative = self._find_find_iterative_in_class(node)
            has_union = self._find_union_in_class(node)
            has_connected = self._find_connected_in_class(node)
            has_rank = self._find_rank_in_class(node)

            if not has_find_recursive and not has_find_iterative and not has_union:
                continue

            evidence.append(
                EvidenceItem(
                    type="parent_array",
                    description="Parent array initialized for disjoint set",
                    location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                    weight=0.25,
                )
            )

            if has_find_recursive:
                evidence.append(
                    EvidenceItem(
                        type="find_recursive",
                        description="Recursive find with path compression",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

            if has_find_iterative:
                evidence.append(
                    EvidenceItem(
                        type="find_iterative",
                        description="Iterative find with path compression",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

            if has_union:
                evidence.append(
                    EvidenceItem(
                        type="union_operation",
                        description="Union operation merging two disjoint sets",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

            if has_connected:
                evidence.append(
                    EvidenceItem(
                        type="connected_check",
                        description="Connected check using find on both elements",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
                    )
                )

            if has_rank:
                evidence.append(
                    EvidenceItem(
                        type="rank_optimization",
                        description="Union by rank/size for balanced tree",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

    def _find_parent_array_in_class(self, class_def: ast.ClassDef) -> bool:
        for child in ast.walk(class_def):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Attribute):
                        if target.attr == "parent":
                            val = child.value
                            if isinstance(val, ast.Call):
                                if isinstance(val.func, ast.Name) and val.func.id in ("list", "range"):
                                    return True
                            if isinstance(val, ast.ListComp):
                                return True
                            if isinstance(val, ast.List):
                                return True
        return False

    def _find_find_recursive_in_class(self, class_def: ast.ClassDef) -> bool:
        for item in class_def.body:
            if isinstance(item, ast.FunctionDef):
                if self._is_find_function(item):
                    if self._has_recursive_self_call(item):
                        if self._has_parent_assignment_in_find(item):
                            return True
        return False

    def _find_find_iterative_in_class(self, class_def: ast.ClassDef) -> bool:
        for item in class_def.body:
            if isinstance(item, ast.FunctionDef):
                if self._is_find_function(item):
                    if self._has_while_loop_in_find(item):
                        if self._has_parent_assignment_in_find(item):
                            return True
        return False

    def _find_union_in_class(self, class_def: ast.ClassDef) -> bool:
        for item in class_def.body:
            if isinstance(item, ast.FunctionDef):
                if self._is_union_function(item):
                    return True
        return False

    def _find_connected_in_class(self, class_def: ast.ClassDef) -> bool:
        for item in class_def.body:
            if isinstance(item, ast.FunctionDef):
                name = item.name.lower()
                if "connect" in name or name == "same" or "isconnected" in name:
                    for sub in ast.walk(item):
                        if isinstance(sub, ast.Call):
                            if isinstance(sub.func, ast.Attribute) and sub.func.attr in ("find", "f"):
                                return True
        return False

    def _is_find_function(self, func_def: ast.FunctionDef) -> bool:
        return "find" in func_def.name.lower() or func_def.name == "f"

    def _is_union_function(self, func_def: ast.FunctionDef) -> bool:
        name = func_def.name.lower()
        return "union" in name or name in ("unite", "merge", "join")

    def _has_recursive_self_call(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if isinstance(child.func.value, ast.Name) and child.func.value.id == "self":
                        if child.func.attr == func_def.name:
                            return True
                if isinstance(child.func, ast.Name) and child.func.id == func_def.name:
                    return True
        return False

    def _has_parent_assignment_in_find(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Subscript):
                        if isinstance(target.value, ast.Attribute):
                            if target.value.attr == "parent":
                                if isinstance(target.value.value, ast.Name) and target.value.value.id == "self":
                                    return True
                        if isinstance(target.value, ast.Name) and target.value.id == "parent":
                            return True
        return False

    def _has_while_loop_in_find(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.While):
                return True
        return False

    def _find_rank_in_class(self, class_def: ast.ClassDef) -> bool:
        rank_vars = set()
        for child in ast.walk(class_def):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Attribute):
                        name = target.attr.lower()
                        if "rank" in name or "size" in name:
                            rank_vars.add(target.attr)
        for child in ast.walk(class_def):
            if isinstance(child, ast.If):
                if isinstance(child.test, ast.Compare):
                    for side in (child.test.left, child.test.comparators[0]):
                        if isinstance(side, ast.Subscript):
                            if isinstance(side.value, ast.Attribute):
                                if side.value.attr in rank_vars:
                                    return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
