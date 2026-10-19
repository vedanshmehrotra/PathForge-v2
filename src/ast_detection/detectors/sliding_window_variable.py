"""Detector for sliding window variable size pattern.

Detects variable-size sliding window where the window expands
and shrinks dynamically based on a condition, typically used
for substring problems, longest/shortest subarray problems.

Does NOT detect fixed-size sliding window patterns.
"""

import ast
from src.ast_detection.window_structure import range_driver, variable_window_link, jump_window_link
from src.ast_detection.python_structure import bindings
from src.ast_detection.structural_qualification import _unshadowed
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


@register_detector
class SlidingWindowVariableDetector(BaseDetector):
    pattern_id = "sliding_window_variable"

    def detect(self, ast_root: ast.AST) -> DetectionResult:
        evidence = []
        parents = {child: node for node in ast.walk(ast_root) for child in ast.iter_child_nodes(node)}
        # Only lexical siblings may initialize a loop's trailing boundary.
        for parent in ast.walk(ast_root):
            for _, body in ast.iter_fields(parent):
                if not isinstance(body, list):
                    continue
                for index, loop in enumerate(body):
                    if not isinstance(loop, ast.For):
                        continue
                    owner = parents.get(loop)
                    while owner is not None and not isinstance(owner, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef)):
                        owner = parents.get(owner)
                    if not _unshadowed(ast_root, owner, 'range', 'enumerate'):
                        continue
                    lead = range_driver(loop)
                    aliases = {}
                    iterator = loop.iter
                    if (lead is None and isinstance(loop.target, ast.Tuple) and len(loop.target.elts) == 2
                            and all(isinstance(n, ast.Name) for n in loop.target.elts)
                            and isinstance(iterator, ast.Call) and isinstance(iterator.func, ast.Name)
                            and iterator.func.id == 'enumerate' and len(iterator.args) == 1
                            and isinstance(iterator.args[0], ast.Name) and not iterator.keywords
                            and not any(bindings(loop.body, n.id) for n in loop.target.elts)):
                        lead = loop.target.elts[0].id
                        aliases[loop.target.elts[1].id] = ast.Subscript(value=iterator.args[0],
                            slice=ast.Name(id=lead, ctx=ast.Load()), ctx=ast.Load())
                    if lead is None:
                        continue
                    link = variable_window_link(loop, lead, body[:index], aliases, products=True)
                    if not link and _unshadowed(ast_root, owner, 'max'):
                        link = jump_window_link(loop, lead, body[:index], aliases)
                    if not link:
                        continue
                    protected = {link.get(k) for k in ('state', 'sequence', 'mapping', 'leading', 'trailing')} - {None}
                    escaped = any(
                        isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) for t in n.targets)
                        and isinstance(n.value, ast.Name) and n.value.id in protected
                        or isinstance(n, ast.Call) and any(isinstance(a, ast.Name) and a.id in protected for a in n.args)
                        and not (isinstance(n.func, ast.Name) and n.func.id in ('max', 'min', 'len', 'sum', 'print', 'range', 'enumerate'))
                        for n in ast.walk(loop)
                    )
                    if escaped:
                        continue
                    evidence.extend([
                        EvidenceItem(type='window_expand', description='Indexed incoming boundary linked to content',
                                     location=f'{loop.lineno}:{loop.col_offset}', weight=0.20),
                        EvidenceItem(type='window_shrink_variable', description='Linked removal or guarded last-seen boundary jump',
                                     location=link.get('outgoing_ref', link.get('update_ref')), weight=0.40 if link['kind']=='variable' else 0.35),
                    ])
                    if link['kind'] == 'variable':
                        evidence.append(EvidenceItem(type='window_validity_check', description='Controlling content/boundary predicate',
                            location=link['guard_ref'], weight=0.30))

        confidence = self._calculate_confidence(evidence)
        return DetectionResult(
            pattern_id=self.pattern_id,
            confidence=confidence,
            evidence=evidence,
            detected=confidence > 0.0,
        )

    def _calculate_confidence(self, evidence: list) -> float:
        if not evidence:
            return 0.0
        total = sum(item.weight for item in evidence)
        return min(total, 1.0)
