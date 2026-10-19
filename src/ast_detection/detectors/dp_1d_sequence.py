"""Detector for 1D sequence DP pattern.

Detects structural evidence of 1D sequence dynamic programming with
nested loops, where each position i depends on previous positions j < i.
Characteristic of Longest Increasing Subsequence (LIS), Russian Doll
Envelopes, and sequence partitioning.
"""

import ast
from src.ast_detection.recurrence_links import sequence_recurrences
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class DP1DSequenceDetector(BaseDetector):
    pattern_id = "dp_1d_sequence"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        for function, outer, statement, table in sequence_recurrences(ast_root):
            for kind, weight in [('nested_fill_loops',0.25), ('inner_lookback',0.25),
                                 ('dp_array_1d',0.25), ('recurrence_expression',0.20)]:
                evidence.append(EvidenceItem(type=kind, description='Initialized table recurrence links the outer state to a prior inner position',
                    location=f'{statement.lineno}:{statement.col_offset}', weight=weight))
            if any(isinstance(n, ast.Return) and isinstance(n.value, ast.Call)
                   and isinstance(n.value.func, ast.Name) and n.value.func.id in ('min','max')
                   and any(isinstance(a, ast.Name) and a.id == table for a in n.value.args)
                   for n in ast.walk(function)):
                evidence.append(EvidenceItem(type='result_aggregation', description='Aggregate the linked recurrence table',weight=0.20))
        return DetectionResult(pattern_id=self.pattern_id, confidence=self._calculate_confidence(evidence),
                               evidence=evidence, detected=bool(evidence))


    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
