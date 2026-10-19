"""Rotated search requires linked interval/midpoint/sorted-half/range updates.

Only local ordered range predicates are supported. Helper calls, disconnected
clauses, rebinding and arbitrary Boolean implications confer no evidence.
"""
import ast

from src.ast_detection.python_structure import bindings, scope_nodes
from src.ast_detection.detectors.binary_search_classic import BinarySearchClassicDetector
from src.ast_detection.detectors.base import BaseDetector, register_detector, DetectionResult, EvidenceItem


def _edges(test):
    if isinstance(test, ast.Compare) and all(isinstance(op, (ast.Lt, ast.LtE)) for op in test.ops):
        values = [test.left, *test.comparators]
        return list(zip(values, values[1:]))
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
        parts = [_edges(v) for v in test.values]
        return [p for part in parts for p in part] if all(parts) else []
    return []


@register_detector
class BinarySearchRotatedDetector(BaseDetector):
    pattern_id = 'binary_search_rotated'

    def detect(self, ast_root):
        evidence = []
        for loop in ast.walk(ast_root):
            if isinstance(loop, ast.While) and self._linked(loop):
                for kind, weight in [('rotated_midpoint',0.20), ('sorted_half_comparison',0.35),
                                     ('target_range_check',0.25), ('rotated_boundary_update',0.25)]:
                    evidence.append(EvidenceItem(type=kind,
                        description='One interval and midpoint control the same sequence half, target range and narrowing updates',
                        location=f'{loop.lineno}:{loop.col_offset}',weight=weight))
        return DetectionResult(pattern_id=self.pattern_id, confidence=min(sum(e.weight for e in evidence),1.0),
                               evidence=evidence, detected=bool(evidence))

    def _linked(self, loop):
        test=loop.test
        if not (isinstance(test, ast.Compare) and len(test.ops)==1 and isinstance(test.ops[0], (ast.Lt,ast.LtE))
                and isinstance(test.left,ast.Name) and isinstance(test.comparators[0],ast.Name)):
            return False
        low, high=test.left.id,test.comparators[0].id
        if low==high:
            return False
        for position, statement in enumerate(loop.body):
            if not (isinstance(statement,ast.Assign) and len(statement.targets)==1
                    and isinstance(statement.targets[0],ast.Name)
                    and BinarySearchClassicDetector._midpoint_uses_bounds(statement.value,low,high)):
                continue
            mid=statement.targets[0].id
            following=loop.body[position+1:]
            if mid in (low,high) or bindings(following,mid):
                continue
            def read(value):
                if (isinstance(value,ast.Subscript) and isinstance(value.value,ast.Name)
                        and isinstance(value.slice,ast.Name) and value.slice.id in (low,mid,high)):
                    return value.value.id,value.slice.id
                return None
            def update(body,bound,operator):
                return len(body)==1 and isinstance(body[0],ast.Assign) and len(body[0].targets)==1 and (
                    isinstance(body[0].targets[0],ast.Name) and body[0].targets[0].id==bound
                    and isinstance(body[0].value,ast.BinOp) and isinstance(body[0].value.op,operator)
                    and isinstance(body[0].value.left,ast.Name) and body[0].value.left.id==mid
                    and isinstance(body[0].value.right,ast.Constant) and type(body[0].value.right.value) is int
                    and body[0].value.right.value==1)
            linked_updates = set()
            for half in following:
                # Only a direct sorted-half decision supplies a range context.
                candidates = [half]
                while candidates:
                    half = candidates.pop()
                    if not (isinstance(half,ast.If) and isinstance(half.test,ast.Compare) and len(half.test.ops)==1
                            and isinstance(half.test.ops[0],(ast.Lt,ast.LtE,ast.Gt,ast.GtE))):
                        continue
                    a,b=read(half.test.left),read(half.test.comparators[0])
                    if not a or not b or a[0]!=b[0] or {a[1],b[1]} not in ({low,mid},{mid,high}):
                        continue
                    sequence=a[0]
                    if bindings(following,sequence):
                        continue
                    candidates.extend(half.orelse)
                    for guard in [*half.body,*half.orelse]:
                        if not isinstance(guard,ast.If):
                            continue
                        edges=_edges(guard.test)
                        if len(edges)!=2:
                            continue
                        (a,b),(c,d)=edges
                        start,end=read(a),read(d)
                        if not (start and end and start[0]==end[0]==sequence and isinstance(b,ast.Name)
                                and isinstance(c,ast.Name) and b.id==c.id and b.id not in (low,high,mid,sequence)
                                and not bindings(loop.body,b.id)):
                            continue
                        if ((start[1],end[1])==(low,mid) and update(guard.body,high,ast.Sub)
                                and update(guard.orelse,low,ast.Add)):
                            linked_updates.update([*guard.body, *guard.orelse])
                        if ((start[1],end[1])==(mid,high) and update(guard.body,low,ast.Add)
                                and update(guard.orelse,high,ast.Sub)):
                            linked_updates.update([*guard.body, *guard.orelse])
            if linked_updates and all(
                n in linked_updates for n in scope_nodes(following)
                if isinstance(n, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id in (low, high) for t in n.targets)
                and any(isinstance(a, ast.Name) and a.id == mid for a in ast.walk(n.value))
            ):
                return True
        return False
