"""Detector for greedy local optimization pattern.

Detects structural evidence of greedy local choice algorithms where
a locally optimal decision is made at each step with the expectation
of finding a global optimum. Characteristic of maximum subarray,
jump game, best time to buy/sell stock, and similar problems.

Does NOT detect:
- Ordinary iteration without local optimum selection
- Dynamic programming (state-based optimization)
- Divide and conquer approaches
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class GreedyLocalDetector(BaseDetector):
    pattern_id = "greedy_local"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_greedy_local(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_optimum_selection = any(e.type == "local_optimum_selection" for e in evidence)
        has_decision = any(e.type == "immediate_decision" for e in evidence)
        has_progress = any(e.type == "forward_progress" for e in evidence)

        detected = has_optimum_selection or (has_decision and has_progress)

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_greedy_local(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if not isinstance(node, ast.FunctionDef):
                continue

            has_optimum = self._find_local_optimum_selection(node)
            has_decision = self._find_immediate_decision(node)
            has_progress = self._find_forward_progress(node)

            if has_optimum:
                evidence.append(
                    EvidenceItem(
                        type="local_optimum_selection",
                        description="Local optimum selection via max/min or running best",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.35,
                    )
                )

            if has_decision:
                evidence.append(
                    EvidenceItem(
                        type="immediate_decision",
                        description="Immediate decision committing to a locally optimal choice",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.30,
                    )
                )

            if has_progress:
                evidence.append(
                    EvidenceItem(
                        type="forward_progress",
                        description="Forward progress via index/pointer advancing monotonically",
                        location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                        weight=0.25,
                    )
                )

    def _find_local_optimum_selection(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id in ("max", "min"):
                    if child.keywords or len(child.args) >= 1:
                        return True
            if isinstance(child, ast.Assign):
                if len(child.targets) == 1 and isinstance(child.targets[0], ast.Name):
                    target = child.targets[0].id.lower()
                    if any(kw in target for kw in ("best", "max", "min", "optimum", "optimal", "profit", "gain", "max_val", "min_val")):
                        if isinstance(child.value, ast.BinOp) and isinstance(child.value.op, (ast.Add, ast.Sub)):
                            return True
                        if isinstance(child.value, ast.Call):
                            if isinstance(child.value.func, ast.Name) and child.value.func.id in ("max", "min"):
                                return True
            if isinstance(child, ast.AugAssign):
                if isinstance(child.target, ast.Name):
                    target = child.target.id.lower()
                    if any(kw in target for kw in ("max", "min", "best", "profit")):
                        return True
        return False

    def _find_immediate_decision(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.If):
                if isinstance(child.test, ast.Compare):
                    for side in (child.test.left, child.test.comparators[0]):
                        if isinstance(side, ast.Name):
                            name = side.id.lower()
                            if any(kw in name for kw in ("profit", "price", "val", "curr", "best", "max", "min")):
                                for stmt in child.body:
                                    if isinstance(stmt, ast.Assign):
                                        return True
                                    if isinstance(stmt, ast.AugAssign):
                                        return True
        return False

    def _find_forward_progress(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.For):
                if isinstance(child.iter, ast.Call):
                    if isinstance(child.iter.func, ast.Name) and child.iter.func.id == "range":
                        for stmt in ast.walk(child):
                            if isinstance(stmt, ast.AugAssign):
                                if isinstance(stmt.target, ast.Name):
                                    target = stmt.target.id.lower()
                                    if target in ("i", "j", "k", "idx", "pos", "index", "left", "right", "l", "r"):
                                        if isinstance(stmt.op, ast.Add):
                                            return True
            if isinstance(child, ast.While):
                for stmt in ast.walk(child):
                    if isinstance(stmt, ast.AugAssign):
                        if isinstance(stmt.target, ast.Name):
                            target = stmt.target.id.lower()
                            if target in ("i", "j", "k", "idx", "pos", "index", "left", "right", "l", "r"):
                                if isinstance(stmt.op, ast.Add):
                                    return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
