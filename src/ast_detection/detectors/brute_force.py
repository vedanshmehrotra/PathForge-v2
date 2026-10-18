"""Exhaustive candidate enumeration; never a judgment of optimality.

Loop nesting and recursion counts alone do not qualify. The shared structural
checks connect enumeration drivers to candidate use or recursive choices.
"""
import ast
from src.ast_detection.python_structure import recursive_calls, scope_nodes
from src.ast_detection.structural_qualification import exhaustive_regions
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class BruteForceDetector(BaseDetector):
    pattern_id = "brute_force"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        for region in exhaustive_regions(ast_root):
            nodes = [region, *scope_nodes(region.body)]
            location = f"{region.lineno}:{region.col_offset}"
            if isinstance(region, ast.FunctionDef):
                calls = recursive_calls(ast_root, region)
                evidence.append(EvidenceItem(type="recursive_branching",
                    description="Bound recursion explores linked candidate choices",
                    location=location, weight=0.20 if len(calls) >= 2 else 0.25))
            else:
                evidence.append(EvidenceItem(type="nested_loops",
                    description="Fresh enumeration drivers are linked to candidate use",
                    location=location, weight=0.35))
            for node in nodes:
                if (isinstance(node, ast.For) and isinstance(node.iter, ast.Call)
                        and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range"):
                    evidence.append(EvidenceItem(type="range_enumeration",
                        description="Range enumerates choices in a qualified region",
                        location=f"{node.lineno}:{node.col_offset}", weight=0.20))
                if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and any(
                    isinstance(n, ast.Subscript) for n in scope_nodes([node.test])
                ):
                    evidence.append(EvidenceItem(type="pair_wise_check",
                        description="Indexed candidate predicate in a qualified enumeration",
                        location=f"{node.lineno}:{node.col_offset}", weight=0.25))
        return DetectionResult(pattern_id=self.pattern_id, detected=bool(evidence),
            evidence=evidence, confidence=min(sum(e.weight for e in evidence), 1.0))
