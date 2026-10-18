"""Bounded local-choice evidence, not max/min spelling or an optimality claim.

Qualification links a choice to subsequent state, reward, reachability or
ordered-neighbor propagation. Reporting an extremum by itself is insufficient.
"""
import ast
from src.ast_detection.python_structure import scope_nodes
from src.ast_detection.structural_qualification import greedy_regions
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class GreedyLocalDetector(BaseDetector):
    pattern_id = "greedy_local"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        seen = set()
        for scope, loop, choice in greedy_regions(ast_root):
            if loop in seen:
                continue
            seen.add(loop)
            location = f"{choice.lineno}:{choice.col_offset}"
            evidence.append(EvidenceItem(type="local_optimum_selection",
                description="Linked local choice affects subsequent work, not only a reporting best",
                location=location, weight=0.35))
            if any(isinstance(n, ast.If) and choice in scope_nodes(n.body) for n in scope_nodes(loop.body)):
                evidence.append(EvidenceItem(type="immediate_decision",
                    description="The linked choice is committed under its controlling predicate",
                    location=location, weight=0.30))
        return DetectionResult(pattern_id=self.pattern_id, detected=bool(evidence),
            evidence=evidence, confidence=min(sum(e.weight for e in evidence), 1.0))
