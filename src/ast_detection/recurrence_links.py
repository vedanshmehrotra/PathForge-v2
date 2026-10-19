"""Bounded recurrence relationships, independent of table/index spelling.

Recognizing a recurrence is evidence of a DP form, not proof of its boundary
conditions, functional correctness, complexity or suitability for a problem.
"""
import ast

from src.ast_detection.python_structure import assignment_values, bindings, scope_nodes
from src.ast_detection.structural_qualification import _initials, _unshadowed


def same(a, b):
    # Read/write contexts differ for the same table cell.
    return ast.unparse(a) == ast.unparse(b)


def offset(node, identifier):
    if isinstance(node, ast.Name) and node.id == identifier:
        return 0
    if (isinstance(node, ast.BinOp) and isinstance(node.left, ast.Name) and node.left.id == identifier
            and isinstance(node.right, ast.Constant) and type(node.right.value) is int
            and isinstance(node.op, (ast.Add, ast.Sub))):
        return node.right.value * (1 if isinstance(node.op, ast.Add) else -1)
    return None


def range_index(loop):
    if (isinstance(loop, ast.For) and isinstance(loop.target, ast.Name)
            and isinstance(loop.iter, ast.Call) and isinstance(loop.iter.func, ast.Name)
            and loop.iter.func.id == 'range' and 1 <= len(loop.iter.args) <= 2 and not loop.iter.keywords):
        return loop.target.id
    return None


def _filled(value):
    return (isinstance(value, ast.BinOp) and isinstance(value.op, ast.Mult)
            and isinstance(value.left, ast.List) and len(value.left.elts) == 1)


def sequence_recurrences(root):
    found = []
    for function in ast.walk(root):
        if not isinstance(function, ast.FunctionDef):
            continue
        if not _unshadowed(root, function, 'range', 'min', 'max'):
            continue
        for position, outer in enumerate(function.body):
            tables = {key for key, value in _initials(function.body[:position]).items() if _filled(value)}
            i = range_index(outer)
            if not i:
                continue
            for inner in scope_nodes(outer.body):
                j = range_index(inner)
                if not j or i == j or offset(inner.iter.args[-1], i) not in (0, 1):
                    continue
                for statement in scope_nodes(inner.body):
                    if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
                        continue
                    target, value = statement.targets[0], statement.value
                    if not (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                            and target.value.id in tables and offset(target.slice, i) == 0
                            and isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                            and value.func.id in ('min', 'max') and len(value.args) == 2
                            and any(same(a, target) for a in value.args)):
                        continue
                    if any(isinstance(n, ast.Subscript) and same(n.value, target.value)
                           and offset(n.slice, j) in (0, -1) for n in ast.walk(value)):
                        found.append((function, outer, statement, target.value.id))
    return found


def grid_row_recurrences(root):
    """An explicit previous-row append or a repeated in-place row recurrence."""
    found = []
    for function in ast.walk(root):
        if not isinstance(function, ast.FunctionDef):
            continue
        if not _unshadowed(root, function, 'range'):
            continue
        initial = {}
        for outer in function.body:
            i = range_index(outer)
            if not i:
                initial.update(assignment_values(outer))
                continue
            rows = {key: value for s in outer.body for key, value in assignment_values(s).items() if _filled(value)}
            for inner in outer.body:
                j = range_index(inner)
                if not j or i == j:
                    continue
                for statement in inner.body:
                    if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
                        continue
                    target, value = statement.targets[0], statement.value
                    if not (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                            and offset(target.slice, j) == 0 and isinstance(value, ast.BinOp)
                            and isinstance(value.op, ast.Add)):
                        continue
                    table = target.value.id
                    if bindings(inner.body, table):
                        continue
                    # Rolling row: same-column previous row plus this row's
                    # preceding column, repeated along an independent axis.
                    if table in initial and _filled(initial[table]):
                        if any(same(a, target) and isinstance(b, ast.Subscript) and same(b.value, target.value)
                               and offset(b.slice, j) == -1 for a,b in ((value.left,value.right),(value.right,value.left))):
                            found.append((function, outer, statement))
                    # New row committed to the same history whose previous row
                    # provides the two neighbors. A detached second table fails.
                    if table not in rows:
                        continue
                    a, b = value.left, value.right
                    if not (isinstance(a, ast.Subscript) and isinstance(b, ast.Subscript)
                            and isinstance(a.value, ast.Subscript) and same(a.value, b.value)
                            and isinstance(a.value.value, ast.Name) and offset(a.value.slice, i) == -1
                            and {offset(a.slice,j),offset(b.slice,j)} == {-1,0}):
                        continue
                    history = a.value.value.id
                    if not isinstance(initial.get(history), ast.List):
                        continue
                    if any(isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
                           and isinstance(s.value.func, ast.Attribute) and s.value.func.attr == 'append'
                           and isinstance(s.value.func.value, ast.Name) and s.value.func.value.id == history
                           and len(s.value.args) == 1 and isinstance(s.value.args[0], ast.Name)
                           and s.value.args[0].id == table for s in outer.body[outer.body.index(inner)+1:]):
                        found.append((function, outer, statement))
    return found
