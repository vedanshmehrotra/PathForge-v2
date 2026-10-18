"""Linked qualification for generic legacy claims, not an optimality prover.

Raw loops/max/min remain observations. These bounded recognizers require the
relationships described in docs/architecture/EVIDENCE_QUALIFICATION.md. Unknown
calls, dynamic state shapes and borrowed scopes do not establish those links.
"""
import ast
import copy

from src.ast_detection.python_structure import (
    assignment_values, bindings, parameter_names, recursive_calls, scope_nodes,
)


def _same(a, b):
    return ast.unparse(a) == ast.unparse(b)


def _expanded(expression, aliases):
    """Resolve saved local expressions on a copy; never mutate submitted syntax."""
    class Expand(ast.NodeTransformer):
        def visit_Name(self, node):
            return copy.deepcopy(aliases.get(node.id, node))
    return Expand().visit(copy.deepcopy(expression))


def _pure_expression(expression):
    return not any(isinstance(n, (ast.NamedExpr, ast.Await, ast.Yield, ast.Lambda))
                   or isinstance(n, ast.Call) and not (
                       isinstance(n.func, ast.Name) and n.func.id in ('min', 'max', 'len', 'list', 'tuple', 'set')
                   ) for n in ast.walk(expression))


def _invalidates_alias(statement, name):
    if bindings([statement], name):
        return True
    for node in scope_nodes([statement]):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name) and node.value.id == name:
            return True  # possible mutable escape; do not infer points-to identity
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == name:
                return True
            if (not isinstance(node.func, ast.Name) or node.func.id not in ('min', 'max', 'len', 'list', 'tuple', 'set', 'print')):
                if any(name in _names(arg) for arg in node.args):
                    return True
    return False


def _names(expression):
    return {n.id for n in scope_nodes([expression]) if isinstance(n, ast.Name)}


def _scopes(root):
    return [n for n in ast.walk(root) if isinstance(n, (ast.Module, ast.FunctionDef))]


def _unshadowed(root, scope, *identifiers):
    parents = {child: parent for parent in ast.walk(root) for child in ast.iter_child_nodes(parent)}
    while scope is not None:
        if isinstance(scope, (ast.Module, ast.FunctionDef)) and any(
            bindings(scope.body, name)
            or isinstance(scope, ast.FunctionDef) and name in parameter_names(scope)
            for name in identifiers
        ):
            return False
        scope = parents.get(scope)
    return True


def _known_numeric_calls(root, scope, loop):
    """Do not assume opaque calls preserve state; no general effect prover."""
    known = {'min', 'max', 'len', 'range', 'abs', 'float', 'int', 'print'}
    return all(isinstance(n.func, ast.Name) and n.func.id in known
               and _unshadowed(root, scope, n.func.id)
               for n in scope_nodes(loop.body) if isinstance(n, ast.Call))


def _loops(body):
    for position, node in enumerate(body):
        if isinstance(node, (ast.For, ast.While)):
            yield node, body[:position]
        if isinstance(node, (ast.For, ast.While, ast.If)):
            yield from _loops(node.body)
            yield from _loops(node.orelse)


def _initials(preceding):
    values = {}
    for statement in preceding:
        for name in list(values):
            if bindings([statement], name):
                values.pop(name)
        values.update(assignment_values(statement))
    return values


def _pairs(statement):
    """Assignment RHS links, including explicit fixed/table-cell writes."""
    if isinstance(statement, ast.AnnAssign) and statement.value is not None:
        return [(statement.target, statement.value)]
    if not isinstance(statement, ast.Assign):
        return []
    result = []

    def collect(target, value):
        if isinstance(target, (ast.Name, ast.Subscript)):
            result.append((target, value))
            return True
        if (isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List))
                and len(target.elts) == len(value.elts)):
            return all(collect(t, v) for t, v in zip(target.elts, value.elts))
        return False

    return result if all(collect(t, statement.value) for t in statement.targets) else []


def _for_index(loop):
    if not isinstance(loop, ast.For) or not isinstance(loop.target, ast.Name):
        return None
    if (isinstance(loop.iter, ast.Call) and isinstance(loop.iter.func, ast.Name)
            and loop.iter.func.id == 'range' and not loop.iter.keywords
            and 1 <= len(loop.iter.args) <= 3 and not bindings(loop.body, loop.target.id)):
        return loop.target.id
    return None


def _driver(loop, preceding):
    """A fresh enumeration driver; a consuming trailing pointer is not reset."""
    if isinstance(loop, ast.For) and isinstance(loop.target, ast.Name):
        if bindings(loop.body, loop.target.id):
            return None
        if _for_index(loop) or isinstance(loop.iter, ast.Name):
            return loop.target.id
    if (isinstance(loop, ast.While) and isinstance(loop.test, ast.Compare)
            and len(loop.test.ops) == 1 and isinstance(loop.test.left, ast.Name)
            and isinstance(loop.test.ops[0], (ast.Lt, ast.LtE))):
        name = loop.test.left.id
        initial = _initials(preceding).get(name)
        if not (isinstance(initial, ast.Constant) and type(initial.value) is int and initial.value == 0):
            return None
        updates = [s for s in loop.body if isinstance(s, ast.AugAssign)
                   and isinstance(s.target, ast.Name) and s.target.id == name
                   and isinstance(s.op, ast.Add) and isinstance(s.value, ast.Constant)
                   and type(s.value.value) is int and s.value.value == 1]
        if len(updates) == 1 and len(bindings(loop.body, name)) == 1:
            return name
    return None


def _bare_names(expression):
    # Index coordinates alone are not a combination of candidate values.
    if isinstance(expression, ast.Subscript):
        return set()
    result = {expression.id} if isinstance(expression, ast.Name) else set()
    if not isinstance(expression, (ast.FunctionDef, ast.Lambda)):
        for child in ast.iter_child_nodes(expression):
            result |= _bare_names(child)
    return result


def _candidate_use(inner, a, b):
    for node in scope_nodes(inner.body):
        expression = node.test if isinstance(node, ast.If) else (
            node.value if isinstance(node, (ast.Return, ast.Expr, ast.AugAssign)) else None)
        if expression is None:
            continue
        if isinstance(expression, ast.Call) and not (
            isinstance(expression.func, ast.Name) and expression.func.id == 'print'
            or isinstance(expression.func, ast.Attribute) and expression.func.attr in ('append', 'add')
        ):
            continue
        if {a, b} <= _bare_names(expression):
            return True
        if not isinstance(node, ast.If):
            continue
        reads = [n for n in scope_nodes([expression]) if isinstance(n, ast.Subscript)
                 and isinstance(n.value, ast.Name)]
        # Pair comparisons, including repeated adjacent comparison passes.
        if any(x.value.id == y.value.id and not _same(x.slice, y.slice)
               and b in _names(x.slice) | _names(y.slice) for x in reads for y in reads):
            return True
        # A grid search tests a cell and stops on a candidate. Component
        # visitation/marking without a search result is traversal evidence.
        if (any(isinstance(n, ast.Subscript) and {a, b} <= _names(n.slice) | _names(n.value)
                for n in scope_nodes([expression]))
                and any(isinstance(n, (ast.Return, ast.Break)) for n in scope_nodes(node.body))):
            return True
    return False


def _constructed_candidate(inner, a, b):
    """Both choices flow into a constructed output, through local copies/appends.

    This recognizes generative enumeration without calling arbitrary helpers
    evidence. A grid address remains one cell, not two combined data values.
    """
    def visit(body, aliases, content, mutable):
        def dependencies(expression):
            if isinstance(expression, ast.Name) and expression.id in content:
                return content[expression.id]
            expression = _expanded(expression, aliases)
            if isinstance(expression, ast.Name):
                return {expression.id} & {a, b}
            if isinstance(expression, ast.Subscript):
                return _names(expression.slice) & {a, b} if isinstance(expression.value, ast.Name) else set()
            if isinstance(expression, ast.Call) and not (
                isinstance(expression.func, ast.Name) and expression.func.id in ('list', 'tuple', 'set')
            ):
                return set()
            return set().union(*(dependencies(n) for n in ast.iter_child_nodes(expression)))

        for statement in body:
            if isinstance(statement, ast.If):
                if {a, b} <= dependencies(statement.test):
                    return True
                if visit(statement.body, dict(aliases), dict(content), set(mutable)) or visit(statement.orelse, dict(aliases), dict(content), set(mutable)):
                    return True
                for name in list(aliases.keys() | content.keys()):
                    if _invalidates_alias(statement, name):
                        aliases.pop(name, None)
                        content.pop(name, None)
                continue
            for target, value in _pairs(statement):
                if isinstance(target, ast.Name):
                    if isinstance(value, ast.Name) and value.id in mutable:
                        return False  # unmodeled mutable alias, never borrowed evidence
                    data = dependencies(value)
                    expanded = _expanded(value, aliases)
                    aliases.pop(target.id, None)
                    content[target.id] = data
                    if _pure_expression(expanded):
                        aliases[target.id] = expanded
                    if isinstance(value, (ast.List, ast.Set)) or (
                        isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id in ('list', 'set')
                    ):
                        mutable.add(target.id)
            if isinstance(statement, ast.Return) and statement.value is not None and {a, b} <= dependencies(statement.value):
                return True
            if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
                continue
            call = statement.value
            data = set().union(*(dependencies(arg) for arg in call.args))
            if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
                receiver = call.func.value.id
                if call.func.attr == 'append':
                    if receiver in content:
                        content[receiver] |= data
                        mutable.add(receiver)
                    elif {a, b} <= data:
                        return True
                else:
                    content.pop(receiver, None)
                    aliases.pop(receiver, None)
            elif isinstance(call.func, ast.Name) and call.func.id == 'print' and {a, b} <= data:
                return True
            else:
                for arg in call.args:
                    if isinstance(arg, ast.Name):
                        content.pop(arg.id, None)
                        aliases.pop(arg.id, None)
        return False
    return visit(inner.body, {}, {}, set())


def exhaustive_regions(root):
    """Candidate combinations, bitmask output enumeration or linked recursive choices."""
    regions = []
    for scope in _scopes(root):
        if not _unshadowed(root, scope, 'range', 'print'):
            continue
        for outer, preceding in _loops(scope.body):
            a = _driver(outer, preceding)
            if not a:
                continue
            for inner, before_inner in _loops(outer.body):
                b = _driver(inner, before_inner)
                if not b or b == a:
                    continue
                if isinstance(inner, ast.For) and isinstance(inner.iter, ast.Name) and inner.iter.id == a:
                    continue  # iterating cells of a row, not independent candidates
                if _candidate_use(inner, a, b) or _constructed_candidate(inner, a, b):
                    regions.append(outer)
                    break
                # Exhaustive subset output: a mask chooses which input elements
                # the inner bit loop appends; not merely two nested loops.
                if (isinstance(outer, ast.For) and isinstance(outer.iter, ast.Call)
                        and any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.LShift)
                                for n in outer.iter.args)):
                    for guard in scope_nodes(inner.body):
                        if (isinstance(guard, ast.If) and isinstance(guard.test, ast.BinOp)
                                and isinstance(guard.test.op, ast.BitAnd) and a in _names(guard.test)
                                and any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.LShift)
                                        and b in _names(n.right) for n in ast.walk(guard.test))
                                and any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                                        and n.func.attr == 'append' and b in _names(n)
                                        for n in scope_nodes(guard.body))):
                            regions.append(outer)
        if not isinstance(scope, ast.FunctionDef):
            continue
        calls = recursive_calls(root, scope)
        for loop, preceding in _loops(scope.body):
            index = _for_index(loop)
            if not index:
                continue
            for call in calls:
                if call not in scope_nodes(loop.body):
                    continue
                # A choice is supplied as an argument, or applied to mutable
                # search state before recursion and explicitly undone afterward.
                choice_argument = any(index in _names(arg) and not (
                    isinstance(arg, ast.Subscript) and not isinstance(arg.slice, ast.Slice)
                ) for arg in call.args)
                undo = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                           and n.func.attr in ('pop', 'remove') for n in scope_nodes(loop.body))
                chosen = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                             and n.func.attr in ('append', 'add') and index in _names(n)
                             for n in scope_nodes(loop.body))
                if choice_argument or chosen and undo:
                    regions.append(scope)
        # Scalar decrement branching (e.g. naive Fibonacci), not two child
        # pointers or divide-and-conquer calls on disjoint slices.
        offsets = {(arg.left.id, arg.right.value) for c in calls for arg in c.args
                   if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub)
                   and isinstance(arg.left, ast.Name) and isinstance(arg.right, ast.Constant)
                   and type(arg.right.value) is int and arg.right.value > 0}
        if any(x == y and a != b for x, a in offsets for y, b in offsets):
            regions.append(scope)
    return list(dict.fromkeys(regions))


def _cell(node, index):
    """Symbolic state lane plus current/previous time, never a dynamic lane."""
    if not isinstance(node, ast.Subscript):
        return None
    lane = None
    if isinstance(node.value, ast.Subscript):
        if not (isinstance(node.slice, ast.Constant) and type(node.slice.value) is int):
            return None
        lane, node = node.slice.value, node.value
    if not isinstance(node.value, ast.Name):
        return None
    key = node.slice
    if index is not None and isinstance(key, ast.Name) and key.id == index:
        return ('table', node.value.id, lane), 'current'
    if (index is not None and isinstance(key, ast.BinOp) and isinstance(key.op, ast.Sub)
            and isinstance(key.left, ast.Name) and key.left.id == index
            and isinstance(key.right, ast.Constant) and type(key.right.value) is int and key.right.value == 1):
        return ('table', node.value.id, lane), 'previous'
    if lane is None and isinstance(key, ast.Constant) and type(key.value) is int:
        return ('fixed', node.value.id, key.value), 'fixed'
    return None


def state_machine_regions(root):
    """Mutually loop-carried states with a choice on their recurrence.

    Scalar snapshots and literal tuple updates follow Python evaluation order.
    Table lanes use i-1 -> i; fixed lanes retain their explicit constant index.
    Reporting totals/bests have one-way dependencies, not a state cycle.
    """
    result = []
    for scope in _scopes(root):
        for loop, preceding in _loops(scope.body):
            if not isinstance(loop, ast.For) or any(isinstance(n, (ast.If, ast.For, ast.While,
                       ast.Return, ast.Raise, ast.Break, ast.Continue, ast.FunctionDef,
                       ast.AsyncFunctionDef, ast.ClassDef)) for n in scope_nodes(loop.body)):
                continue
            if not _unshadowed(root, scope, 'max', 'min', 'range'):
                continue
            initial = _initials(preceding)
            index = _for_index(loop)
            if (not _known_numeric_calls(root, scope, loop)
                    or isinstance(loop.iter, ast.Call) and isinstance(loop.iter.func, ast.Name)
                    and loop.iter.func.id == 'range' and len(loop.iter.args) == 3
                    and not (isinstance(loop.iter.args[2], ast.Constant) and loop.iter.args[2].value == 1)):
                continue
            pairs = [pair for s in loop.body for pair in _pairs(s)]
            scalars = {t.id for t, _ in pairs if isinstance(t, ast.Name) and t.id in initial
                       and t.id not in _names(loop.target)}
            cells = {cell[0] for t, _ in pairs if (cell := _cell(t, index))
                     and cell[1] != 'previous' and cell[0][1] in initial}
            keys = {('scalar', s) for s in scalars} | cells
            if len(keys) < 2:
                continue
            arrays = {key[1] for key in cells}
            # Preserve temporal/cell identity. Explicit rebinding, deletion or
            # a mutable alias can invalidate several lanes at once.
            if (any(bindings(loop.body, name) for name in arrays)
                    or any(isinstance(n, ast.Delete) and _names(n) & arrays for n in scope_nodes(loop.body))
                    or any(isinstance(v, ast.Name) and v.id in arrays for _, v in pairs)
                    or any(isinstance(v, ast.Name) and v.id in arrays for v in initial.values())
                    or any(len({k[0] for k in cells if k[1] == name}) > 1 for name in arrays)):
                continue
            empty = (frozenset(), False)
            env = {s: (frozenset({('scalar', s)}), False) for s in scalars}
            current = {key: (frozenset({key}), False) for key in keys if key[0] != 'table'}

            def refs(expression):
                if isinstance(expression, ast.Name):
                    return env.get(expression.id, empty)
                if isinstance(expression, ast.Subscript):
                    cell = _cell(expression, index)
                    if not cell or cell[0] not in cells:
                        return empty
                    return (frozenset({cell[0]}), False) if cell[1] == 'previous' else current.get(cell[0], empty)
                if isinstance(expression, ast.Call):
                    if not (isinstance(expression.func, ast.Name) and expression.func.id in ('min', 'max')
                            and len(expression.args) >= 2 and not expression.keywords):
                        return empty
                    children = [refs(a) for a in expression.args]
                    roots = frozenset().union(*(x[0] for x in children))
                    return roots, bool(roots)
                if isinstance(expression, (ast.BinOp, ast.UnaryOp)):
                    children = [refs(n) for n in ast.iter_child_nodes(expression)]
                    return frozenset().union(*(x[0] for x in children)), any(x[1] for x in children)
                return empty

            for statement in loop.body:
                updates = _pairs(statement)
                values = [(t, refs(v)) for t, v in updates]  # simultaneous RHS evaluation
                if isinstance(statement, ast.AugAssign):
                    old, rhs = refs(statement.target), refs(statement.value)
                    values = [(statement.target, (old[0] | rhs[0], old[1] or rhs[1]))]
                for target, value in values:
                    if isinstance(target, ast.Name):
                        env[target.id] = value
                        if target.id in scalars:
                            current[('scalar', target.id)] = value
                    elif (cell := _cell(target, index)) and cell[0] in cells:
                        current[cell[0]] = value
                if not updates and not isinstance(statement, ast.AugAssign):
                    for name in list(env):
                        if bindings([statement], name):
                            env[name] = empty
                            current[('scalar', name)] = empty
            graph = {key: current.get(key, empty)[0] for key in keys}

            def reaches(start, end, seen=None):
                seen = set(seen or ()) | {start}
                return end in graph[start] or any(reaches(n, end, seen) for n in graph[start] - seen)

            if any(a != b and reaches(a, b) and reaches(b, a)
                   and (current.get(a, empty)[1] or current.get(b, empty)[1]) for a in keys for b in keys):
                result.append((scope, loop, bool(cells)))
    return result


def _current_item(expression, loop):
    if not isinstance(loop, ast.For):
        return False
    if isinstance(loop.target, ast.Name) and isinstance(loop.iter, ast.Name):
        return isinstance(expression, ast.Name) and expression.id == loop.target.id
    index = _for_index(loop)
    return (index is not None and isinstance(expression, ast.Subscript)
            and isinstance(expression.value, ast.Name) and isinstance(expression.slice, ast.Name)
            and expression.slice.id == index)


def _selections(loop, protected):
    """Choices retain branch-local expression snapshots, not name coincidences."""
    choices = []

    def visit(body, aliases):
        for statement in body:
            if isinstance(statement, ast.If):
                test = _expanded(statement.test, aliases)
                if isinstance(test, ast.Compare) and len(test.ops) == 1:
                    for write in statement.body:
                        for target, rhs in _pairs(write):
                            if not isinstance(target, ast.Name):
                                continue
                            value = _expanded(rhs, aliases)
                            if isinstance(test.left, ast.Name) and test.left.id == target.id and _same(test.comparators[0], value):
                                op = 'max' if isinstance(test.ops[0], ast.Lt) else 'min' if isinstance(test.ops[0], ast.Gt) else None
                            elif isinstance(test.comparators[0], ast.Name) and test.comparators[0].id == target.id and _same(test.left, value):
                                op = 'max' if isinstance(test.ops[0], ast.Gt) else 'min' if isinstance(test.ops[0], ast.Lt) else None
                            else:
                                op = None
                            if op:
                                choices.append((target, value, op, write, value))
                visit(statement.body, dict(aliases))
                visit(statement.orelse, dict(aliases))
                for name in list(aliases):
                    if _invalidates_alias(statement, name):
                        aliases.pop(name)
                continue
            pairs = _pairs(statement)
            resolved = [(t, _expanded(v, aliases)) for t, v in pairs]
            for target, value in resolved:
                if not isinstance(target, ast.Name):
                    continue
                if (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                        and value.func.id in ('min', 'max') and len(value.args) == 2 and not value.keywords):
                    for i in range(2):
                        if isinstance(value.args[i], ast.Name) and value.args[i].id == target.id:
                            choices.append((target, value.args[1-i], value.func.id, statement, value))
                    if target.id in _names(value) and not any(
                        isinstance(a, ast.Name) and a.id == target.id for a in value.args
                    ):
                        choices.append((target, value, value.func.id, statement, value))
                aliases.pop(target.id, None)
                if target.id not in protected and _pure_expression(value):
                    aliases[target.id] = value
            if not pairs:
                for name in list(aliases):
                    if bindings([statement], name) or any(
                        isinstance(n, ast.Call) and name in _names(n) for n in scope_nodes([statement])
                    ):
                        aliases.pop(name)
    visit(loop.body, {})
    return choices


def greedy_regions(root):
    """Reviewed local-choice relationships, not a max/min or variable-name test.

    Supports restart/extend, prefix-extreme reward, reachable-frontier selection
    and guarded adjacent relaxation. A reporting best alone supports none.
    """
    regions = []
    for scope in _scopes(root):
        if not _unshadowed(root, scope, 'max', 'min', 'range'):
            continue
        for loop, preceding in _loops(scope.body):
            if not isinstance(loop, ast.For) or any(isinstance(n, (ast.For, ast.While))
                                                  for n in scope_nodes(loop.body)):
                continue
            if not _known_numeric_calls(root, scope, loop):
                continue
            initial = _initials(preceding)
            choices = _selections(loop, set(initial) | _names(loop.target))
            # An unconditional reset/rebinding cannot be borrowed as persistent
            # state merely because a selection also appears elsewhere.
            choices = [c for c in choices if c[0].id in initial and len(bindings(loop.body, c[0].id)) == 1 and all(
                n in [x[0] for x in choices if x[0].id == c[0].id]
                for n in bindings(loop.body, c[0].id)
            )]
            for target, candidate, operation, statement, value in choices:
                state = target.id
                if isinstance(value, ast.Call):
                    # Restart from this input item or extend prior selected
                    # work with that same item; a reduction best=max(best,x)
                    # cannot establish this feedback relationship.
                    for a, b in ((value.args[0], value.args[1]), (value.args[1], value.args[0])):
                        if (_current_item(a, loop) and isinstance(b, ast.BinOp) and isinstance(b.op, ast.Add)
                                and any(isinstance(x, ast.Name) and x.id == state and _same(y, a)
                                        for x, y in ((b.left, b.right), (b.right, b.left)))):
                            regions.append((scope, loop, statement))
                # A prefix extreme is used in another choice's reward, not
                # simply returned as a report of the input's extrema.
                if _current_item(candidate, loop):
                    for other, reward, _, write, _ in choices:
                        if (other.id != state and isinstance(reward, ast.BinOp) and isinstance(reward.op, ast.Sub)
                                and any(isinstance(x, ast.Name) and x.id == state and _same(y, candidate)
                                        for x, y in ((reward.left, reward.right), (reward.right, reward.left)))):
                            regions.append((scope, loop, statement))
                index = _for_index(loop)
                if operation == 'max' and index and isinstance(candidate, ast.BinOp) and isinstance(candidate.op, ast.Add):
                    linked_reach = any(isinstance(x, ast.Name) and x.id == index and _current_item(y, loop)
                                       for x, y in ((candidate.left, candidate.right), (candidate.right, candidate.left)))
                    for guard in scope_nodes(loop.body):
                        if not (linked_reach and isinstance(guard, ast.If) and isinstance(guard.test, ast.Compare)
                                and len(guard.test.ops) == 1 and {index, state} == _names(guard.test)
                                and ((isinstance(guard.test.left, ast.Name) and guard.test.left.id == index
                                      and isinstance(guard.test.ops[0], ast.Gt))
                                     or (isinstance(guard.test.left, ast.Name) and guard.test.left.id == state
                                         and isinstance(guard.test.ops[0], ast.Lt)))
                                and any(isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)
                                        and n.value.value is False for n in scope_nodes(guard.body))):
                            continue
                        regions.append((scope, loop, statement))
            # Adjacent propagation conditional on the input ordering, as in
            # the existing candy implementation. Index and neighbor must agree.
            index = _for_index(loop)
            if not index:
                continue
            for guard in scope_nodes(loop.body):
                if not (isinstance(guard, ast.If) and isinstance(guard.test, ast.Compare)
                        and len(guard.test.ops) == 1 and isinstance(guard.test.ops[0], (ast.Lt, ast.Gt))):
                    continue
                left, right = guard.test.left, guard.test.comparators[0]
                if not (isinstance(left, ast.Subscript) and isinstance(right, ast.Subscript)
                        and isinstance(left.value, ast.Name) and isinstance(right.value, ast.Name)
                        and left.value.id == right.value.id and isinstance(left.slice, ast.Name)
                        and left.slice.id == index and isinstance(right.slice, ast.BinOp)
                        and isinstance(right.slice.op, (ast.Add, ast.Sub))
                        and isinstance(right.slice.left, ast.Name) and right.slice.left.id == index
                        and isinstance(right.slice.right, ast.Constant) and right.slice.right.value == 1):
                    continue
                for statement in guard.body:
                    for target, value in _pairs(statement):
                        if not (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                                and target.value.id in initial and _same(target.slice, left.slice)
                                and isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                                and value.func.id in ('min', 'max') and len(value.args) == 2):
                            continue
                        for a, b in ((value.args[0], value.args[1]), (value.args[1], value.args[0])):
                            if (_same(a, target) and isinstance(b, ast.BinOp) and isinstance(b.op, ast.Add)
                                    and isinstance(b.left, ast.Subscript) and _same(b.left.value, target.value)
                                    and _same(b.left.slice, right.slice) and isinstance(b.right, ast.Constant)
                                    and type(b.right.value) is int and b.right.value > 0):
                                regions.append((scope, loop, statement))
    return list(dict.fromkeys(regions))
