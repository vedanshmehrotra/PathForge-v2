"""Detector for 1D sequence DP pattern.

Detects structural evidence of 1D sequence dynamic programming with
nested loops, where each position i depends on previous positions j < i.
Characteristic of Longest Increasing Subsequence (LIS), Russian Doll
Envelopes, and sequence partitioning.
"""

import ast
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class DP1DSequenceDetector(BaseDetector):
    pattern_id = "dp_1d_sequence"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        self._detect_1d_sequence(ast_root, evidence)

        confidence = self._calculate_confidence(evidence)

        has_nested_loops = any(e.type == "nested_fill_loops" for e in evidence)
        has_inner_lookback = any(e.type == "inner_lookback" for e in evidence)
        has_array = any(e.type == "dp_array_1d" for e in evidence)
        has_recurrence = any(e.type == "recurrence_expression" for e in evidence)
        has_aggregation = any(e.type == "result_aggregation" for e in evidence)

        secondary_count = sum([has_array, has_recurrence, has_aggregation])
        detected = has_nested_loops and has_inner_lookback and secondary_count >= 1

        if self._has_anti_signals(evidence):
            detected = False

        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=detected,
        )

    def _detect_1d_sequence(self, ast_root: ast.AST, evidence: list) -> None:
        for node in ast.walk(ast_root):
            if isinstance(node, ast.FunctionDef):
                has_nested = self._find_nested_fill_loops(node)
                has_lookback = self._find_inner_lookback(node)
                has_array = self._find_dp_array_1d(node)
                has_recurrence = self._find_sequence_recurrence(node)
                has_aggregation = self._find_result_aggregation(node)

                if has_nested:
                    evidence.append(
                        EvidenceItem(
                            type="nested_fill_loops",
                            description="Two-level nested loop filling DP array",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )

                if has_lookback:
                    evidence.append(
                        EvidenceItem(
                            type="inner_lookback",
                            description="dp[j] read inside inner loop for sequence lookback",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )

                if has_array:
                    evidence.append(
                        EvidenceItem(
                            type="dp_array_1d",
                            description="1D DP array created via list multiplication",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.25,
                        )
                    )

                if has_recurrence:
                    evidence.append(
                        EvidenceItem(
                            type="recurrence_expression",
                            description="Recurrence combining dp[i] and dp[j] via max/min",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.20,
                        )
                    )

                if has_aggregation:
                    evidence.append(
                        EvidenceItem(
                            type="result_aggregation",
                            description="Result aggregation via max/min over entire DP array",
                            location=f"{node.lineno}:{node.col_offset}" if hasattr(node, "lineno") else None,
                            weight=0.20,
                        )
                    )

    def _find_nested_fill_loops(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.For):
                for child in ast.walk(node):
                    if isinstance(child, ast.For) and child is not node:
                        has_dp_write = self._has_dp_write_in_loops(node, child)
                        if has_dp_write:
                            return True
        return False

    def _has_dp_write_in_loops(self, outer: ast.For, inner: ast.For) -> bool:
        for node in ast.walk(inner):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Subscript):
                        if isinstance(target.value, ast.Name) and target.value.id.lower().startswith("dp"):
                            return True
        return False

    def _find_inner_lookback(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.For):
                for child in ast.walk(node):
                    if isinstance(child, ast.For) and child is not node:
                        dp_reads = 0
                        for sub in ast.walk(child):
                            if isinstance(sub, ast.Subscript):
                                if isinstance(sub.value, ast.Name) and sub.value.id.lower().startswith("dp"):
                                    if isinstance(sub.slice, ast.Name) and sub.slice.id.lower() in ("j", "k", "prev", "p"):
                                        dp_reads += 1
                                    if isinstance(sub.slice, ast.BinOp):
                                        for inner in ast.walk(sub.slice):
                                            if isinstance(inner, ast.Name) and inner.id.lower() in ("j", "k", "prev", "p"):
                                                dp_reads += 1
                        if dp_reads >= 1:
                            return True
        return False

    def _find_dp_array_1d(self, func_def: ast.FunctionDef) -> bool:
        for child in ast.walk(func_def):
            if isinstance(child, ast.Assign):
                if isinstance(child.value, ast.BinOp) and isinstance(child.value.op, ast.Mult):
                    if isinstance(child.value.left, ast.List):
                        return True
        return False

    def _find_sequence_recurrence(self, func_def: ast.FunctionDef) -> bool:
        has_max_min = False
        for node in ast.walk(func_def):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("max", "min"):
                    has_max_min = True
                    for arg in node.args:
                        if isinstance(arg, ast.BinOp):
                            for sub in ast.walk(arg):
                                if isinstance(sub, ast.Subscript):
                                    if isinstance(sub.value, ast.Name) and sub.value.id.lower().startswith("dp"):
                                        return True
        return False

    def _find_result_aggregation(self, func_def: ast.FunctionDef) -> bool:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Return):
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name) and node.value.func.id in ("max", "min"):
                        for arg in node.value.args:
                            if isinstance(arg, ast.Name) and arg.id.lower().startswith("dp"):
                                return True
        return False

    def _has_anti_signals(self, evidence: list) -> bool:
        has_secondary = any(e.type in ("dp_array_1d", "recurrence_expression", "result_aggregation") for e in evidence)
        has_lookback_only = any(e.type == "inner_lookback" for e in evidence) and not has_secondary
        if has_lookback_only:
            return True
        return False

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
