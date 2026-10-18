"""State-machine DP qualified by loop-carried state relationships.

Mutually dependent old/new states and a choice on the recurrence are required.
A counter, a reporting maximum, or two disconnected assignments cannot qualify.
"""
import ast
from src.ast_detection.python_structure import scope_nodes
from src.ast_detection.structural_qualification import state_machine_regions
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class DPStateMachineDetector(BaseDetector):
    pattern_id = "dp_state_machine"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        for scope, loop, has_array in state_machine_regions(ast_root):
            location = f"{loop.lineno}:{loop.col_offset}"
            evidence.extend([
                EvidenceItem(type="state_variables", description="Distinct loop-carried state lanes",
                             location=location, weight=0.30),
                EvidenceItem(type="state_transition", description="Choice participates in a mutually dependent state recurrence",
                             location=location, weight=0.30),
                EvidenceItem(type="table_fill_loop", description="One loop advances the linked states",
                             location=location, weight=0.20),
            ])
            if has_array:
                evidence.append(EvidenceItem(type="dp_array_1d", description="Explicit fixed or temporal state lanes",
                                             location=location, weight=0.20))
            if any(isinstance(n, ast.Return) and isinstance(n.value, ast.Call)
                   and isinstance(n.value.func, ast.Name) and n.value.func.id == "max"
                   for n in scope_nodes(scope.body)):
                evidence.append(EvidenceItem(type="result_aggregation", description="Result aggregation after qualified state transitions",
                                             location=location, weight=0.20))
        return DetectionResult(pattern_id=self.pattern_id, detected=bool(evidence),
            evidence=evidence, confidence=min(sum(e.weight for e in evidence), 1.0))
