"""Detector for backtracking subset generation pattern.

Detects recursive backtracking algorithms that generate subsets,
combinations, or similar state-space exploration using the
choose/recurse/unchoose pattern.

Does NOT detect:
- Ordinary recursion without state restoration
- Permutation generation (swap-based)
- Simple iteration-based subset generation
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class BacktrackingSubsetDetector(BaseDetector):
    pattern_id = "backtracking_subset"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_backtracking_subset(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_recursive_branching = any(e.type == "recursive_branching" for e in evidence)
        has_choose_recurse_unchoose = any(e.type == "choose_recurse_unchoose" for e in evidence)
        has_state_restoration = any(e.type == "state_restoration" for e in evidence)

        detected = has_choose_recurse_unchoose or (has_recursive_branching and has_state_restoration)

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_backtracking_subset(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.FunctionDef):
                continue

            func_name = node.name

            if not self._has_recursive_call(node, func_name):
                continue

            has_branching = self._find_recursive_branching(node, func_name)
            has_choose_unchoose = self._find_choose_recurse_unchoose(node, func_name)
            has_state = self._find_state_restoration(node)
            has_building = self._find_subset_building(node)

            if not (has_branching or has_choose_unchoose):
                continue

            if has_choose_unchoose:
                evidence.append(
                    EvidenceItem(
                        type="choose_recurse_unchoose",
                        description="Choose/recurse/unchoose pattern with append and pop",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.35,
                    )
                )

            if has_branching:
                evidence.append(
                    EvidenceItem(
                        type="recursive_branching",
                        description="Multiple recursive calls exploring different branches",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

            if has_state:
                evidence.append(
                    EvidenceItem(
                        type="state_restoration",
                        description="State restoration via pop or backtrack after recursion",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

            if has_building:
                evidence.append(
                    EvidenceItem(
                        type="subset_generation",
                        description="Building subset result by adding partial selections",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.20,
                    )
                )

    def _has_recursive_call(self, func_def: ast.FunctionDef, func_name: str) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == func_name:
                    return True
        return False

    def _find_recursive_branching(self, func_def: ast.FunctionDef, func_name: str) -> bool:
        count = 0
        for child in ast.walk(func_def):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == func_name:
                    count += 1
                    if count >= 2:
                        return True
        return False

    def _find_choose_recurse_unchoose(self, func_def: ast.FunctionDef, func_name: str) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute) and child.func.attr == "append":
                    if isinstance(child.func.value, ast.Name):
                        for stmt in ast.walk(func_def):
                            if isinstance(stmt, ast.Call):
                                if isinstance(stmt.func, ast.Name) and stmt.func.id == func_name:
                                    for post in ast.walk(func_def):
                                        if isinstance(post, ast.Expr):
                                            if isinstance(post.value, ast.Call):
                                                if isinstance(post.value.func, ast.Attribute) and post.value.func.attr in ("pop", "pop"):
                                                    return True
        return False

    def _find_state_restoration(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Expr):
                if isinstance(child.value, ast.Call):
                    if isinstance(child.value.func, ast.Attribute):
                        if child.value.func.attr == "pop":
                            return True
            if isinstance(child, ast.AugAssign):
                if isinstance(child.op, ast.Sub):
                    return True
        return False

    def _find_subset_building(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute) and child.func.attr == "append":
                    if isinstance(child.func.value, ast.Name):
                        name = child.func.value.id.lower()
                        if any(kw in name for kw in ("res", "result", "subset", "path", "sol", "curr", "temp", "combo")):
                            return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
