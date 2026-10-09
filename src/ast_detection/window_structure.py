"""Shared AST-only checks for linked window maintenance, with no diagnoses or authority."""
import ast


def scope_nodes(body):
    """Executable nodes in this scope; do not borrow helper or nested-for bodies."""
    for node in body:
        yield node
        if isinstance(node, ast.For):
            # Its target/iterator execute here and can rebind a bound, while
            # its body cannot supply this loop's maintenance evidence.
            yield from scope_nodes([node.target, node.iter])
        elif not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            yield from scope_nodes(ast.iter_child_nodes(node))


def same(a, b):
    return ast.dump(a, include_attributes=False) == ast.dump(b, include_attributes=False)


def name(node, value):
    return isinstance(node, ast.Name) and node.id == value


def unit_advance(statement, variable):
    return (isinstance(statement, ast.AugAssign) and name(statement.target, variable)
            and isinstance(statement.op, ast.Add) and isinstance(statement.value, ast.Constant)
            and type(statement.value.value) is int and statement.value.value == 1) or (
        isinstance(statement, ast.Assign) and len(statement.targets) == 1 and name(statement.targets[0], variable)
        and isinstance(statement.value, ast.BinOp) and isinstance(statement.value.op, ast.Add)
        and name(statement.value.left, variable) and isinstance(statement.value.right, ast.Constant)
        and type(statement.value.right.value) is int and statement.value.right.value == 1)


def range_driver(loop):
    iterator = loop.iter if isinstance(loop, ast.For) else None
    if not (isinstance(iterator, ast.Call) and name(iterator.func, "range") and not iterator.keywords
            and 1 <= len(iterator.args) <= 3 and isinstance(loop.target, ast.Name)):
        return None
    if len(iterator.args) == 3 and not (isinstance(iterator.args[2], ast.Constant) and type(iterator.args[2].value) is int
                                      and iterator.args[2].value == 1):
        return None
    if any((isinstance(n, ast.Name) and n.id == loop.target.id and isinstance(n.ctx, (ast.Store, ast.Del)))
           or (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == loop.target.id)
           for n in scope_nodes(loop.body)):
        return None
    return loop.target.id


def index_read(value, aliases):
    seen = set()
    while isinstance(value, ast.Name) and value.id in aliases and value.id not in seen:
        seen.add(value.id)
        value = aliases[value.id]
    if isinstance(value, ast.Subscript) and isinstance(value.value, ast.Name) and not isinstance(value.slice, ast.Slice):
        return value.value.id, value.slice
    return None


def maintenance_events(body, aliases=None, controls=()):
    """State +/- content observations with lexical guards and direct aliases.

    Scalar counters may depend on an indexed-content guard (e.g. counting
    zeros), rather than an indexed RHS. An event is not itself a window.
    """
    aliases = dict(aliases or {})
    result = []
    for statement in body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.For)):
            continue
        if isinstance(statement, (ast.If, ast.While)):
            result.extend(maintenance_events(statement.body, aliases, (*controls, statement)))
            result.extend(maintenance_events(statement.orelse, aliases, controls))
            continue
        target = None
        signed = []
        if isinstance(statement, ast.AugAssign) and isinstance(statement.op, (ast.Add, ast.Sub)):
            target = statement.target
            direction = 1 if isinstance(statement.op, ast.Add) else -1
            if direction == 1 and isinstance(statement.value, ast.BinOp) and isinstance(statement.value.op, ast.Sub):
                signed = [(1, statement.value.left), (-1, statement.value.right)]
            else:
                signed = [(direction, statement.value)]
        elif isinstance(statement, ast.Assign) and len(statement.targets) == 1:
            target = statement.targets[0]
            value = statement.value
            if isinstance(target, ast.Name):
                if isinstance(value, ast.BinOp) and isinstance(value.op, (ast.Add, ast.Sub)) and name(value.left, target.id):
                    signed = [(1 if isinstance(value.op, ast.Add) else -1, value.right)]
                elif (isinstance(value, ast.BinOp) and isinstance(value.op, ast.Sub)
                      and isinstance(value.left, ast.BinOp) and isinstance(value.left.op, ast.Add)
                      and name(value.left.left, target.id)):
                    signed = [(1, value.left.right), (-1, value.right)]
            elif isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                if isinstance(value, ast.BinOp) and isinstance(value.op, (ast.Add, ast.Sub)):
                    previous = value.left
                    if same(previous, target) or (isinstance(previous, ast.Call) and isinstance(previous.func, ast.Attribute)
                                                and name(previous.func.value, target.value.id) and previous.func.attr == "get"
                                                and previous.args and same(previous.args[0], target.slice)):
                        signed = [(1 if isinstance(value.op, ast.Add) else -1, value.right)]
        elif isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            call = statement.value
            if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and len(call.args) == 1:
                if call.func.attr in ("add", "append", "remove", "discard"):
                    target = call.func.value
                    signed = [(1 if call.func.attr in ("add", "append") else -1, call.args[0])]
        elif isinstance(statement, ast.Delete) and len(statement.targets) == 1:
            target = statement.targets[0]
            if isinstance(target, ast.Subscript):
                signed = [(-1, ast.Constant(value=1))]
        for direction, value in signed:
            state = target.id if isinstance(target, ast.Name) else target.value.id if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) else None
            if not state:
                continue
            read = index_read(target.slice, aliases) if isinstance(target, ast.Subscript) else index_read(value, aliases)
            if not read and isinstance(value, ast.Constant) and type(value.value) is int and value.value == 1:
                for guard in reversed(controls):
                    reads = [index_read(n, aliases) for n in scope_nodes([guard.test]) if isinstance(n, ast.Subscript)]
                    # Prefer the element read over its enclosing frequency
                    # lookup, e.g. s[left] within need[s[left]].
                    reads = [r for r in reads if r and isinstance(r[1], (ast.Name, ast.BinOp))]
                    if len(reads) == 1:
                        read = reads[0]
                        break
            if read:
                result.append({"state": state, "direction": direction, "sequence": read[0], "index": read[1],
                               "node": statement, "controls": controls})
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name):
                    aliases.pop(target.id, None)
                    if isinstance(statement.value, (ast.Name, ast.Subscript)) and not name(statement.value, target.id):
                        aliases[target.id] = statement.value
    return result


def state_updates_linked(body, state, sequence, events):
    known = {e["node"] for e in events if e["state"] == state and e["sequence"] == sequence}
    for node in scope_nodes(body):
        targets = node.targets if isinstance(node, (ast.Assign, ast.Delete)) else [node.target] if isinstance(node, (ast.AugAssign, ast.AnnAssign)) else []
        for target in targets:
            if name(target, state) or isinstance(target, ast.Subscript) and name(target.value, state):
                if node not in known:
                    return False
        if (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute)
                and name(node.value.func.value, state) and node not in known):
            return False
    return True


def linked_trailing_advance(body, guard, trailing, outgoing):
    advances = [s for s in guard.body if unit_advance(s, trailing)]
    if len(advances) != 1:
        return False
    stores = [n for n in scope_nodes(body) if name(n, trailing) and isinstance(n.ctx, (ast.Store, ast.Del))]
    allowed = [n for n in scope_nodes(advances) if name(n, trailing) and isinstance(n.ctx, ast.Store)]
    if stores != allowed:
        return False
    owner = next((s for s in guard.body if outgoing in scope_nodes([s])), None)
    return owner is not None and guard.body.index(owner) < guard.body.index(advances[0])


def _initial_zero(preceding, variable):
    for statement in reversed(preceding):
        if writes_name(statement, variable):
            return (isinstance(statement, ast.Assign) and len(statement.targets) == 1 and name(statement.targets[0], variable)
                    and isinstance(statement.value, ast.Constant) and type(statement.value.value) is int and statement.value.value == 0)
    return False


def _boundary_width(test, lead):
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and name(test.left, lead)
            and isinstance(test.ops[0], (ast.GtE, ast.Gt))):
        return None
    value = test.comparators[0]
    if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Sub) and isinstance(value.right, ast.Constant) and value.right.value == 1:
        return value.left, True
    return value, False


def _stable_width(width, loop, lead):
    if isinstance(width, ast.Name):
        variables = {width.id}
    elif isinstance(width, ast.Constant) and type(width.value) is int and width.value >= 0:
        variables = set()
    elif (isinstance(width, ast.Call) and name(width.func, "len") and len(width.args) == 1
          and not width.keywords and isinstance(width.args[0], ast.Name)):
        variables = {width.args[0].id}
    else:
        return False
    return lead not in variables and not any(writes_name(s, v) for v in variables for s in loop.body)


def boundary_window_link(loop, preceding):
    lead = range_driver(loop)
    if lead is None:
        return None
    events = maintenance_events(loop.body)
    for incoming in events:
        if incoming["direction"] != 1 or not name(incoming["index"], lead):
            continue
        if (not state_updates_linked(loop.body, incoming["state"], incoming["sequence"], events)
                or any(writes_name(s, incoming["sequence"]) for s in loop.body)):
            continue
        for outgoing in events:
            if (outgoing["direction"] != -1 or outgoing["state"] != incoming["state"]
                    or outgoing["sequence"] != incoming["sequence"]):
                continue
            for guard in outgoing["controls"]:
                if not isinstance(guard, ast.If) or guard not in loop.body:
                    continue
                boundary = _boundary_width(guard.test, lead)
                if boundary is None:
                    test = guard.test
                    if (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Gt)
                            and isinstance(test.left, ast.Call) and name(test.left.func, "len") and len(test.left.args) == 1
                            and name(test.left.args[0], incoming["state"])):
                        boundary = test.comparators[0], False
                if boundary is None:
                    continue
                width, uses_pointer = boundary
                if not _stable_width(width, loop, lead):
                    continue
                index = outgoing["index"]
                if isinstance(index, ast.Name) and index.id != lead:
                    advances = [s for s in guard.body if unit_advance(s, index.id)]
                    if (not linked_trailing_advance(loop.body, guard, index.id, outgoing["node"])
                            or not _initial_zero(preceding, index.id)
                            or any(writes_name(s, index.id) for s in loop.body if s is not guard)
                            or any(writes_name(s, index.id) for s in guard.body if s not in advances)):
                        continue
                elif (isinstance(index, ast.BinOp) and isinstance(index.op, ast.Sub) and name(index.left, lead)
                      and same(index.right, width) and not uses_pointer):
                    pass
                else:
                    continue
                return {"kind": "fixed_boundary", "sequence": incoming["sequence"], "state": incoming["state"],
                        "leading": lead, "incoming_ref": f'{incoming["node"].lineno}:{incoming["node"].col_offset}',
                        "outgoing_ref": f'{outgoing["node"].lineno}:{outgoing["node"].col_offset}'}
    return None


def has_offset_window_update(loop: ast.For, preceding: list) -> bool:
    """Recognize initialized, straight-line sum windows without a boundary if.

    Require sum(sequence[:width]), range(width, stop) with unit advance,
    and incoming[index] minus outgoing[index-width] on one accumulator.
    Width/index/sequence changes or other accumulator writes fail closed.
    """
    iterator = loop.iter
    if not (isinstance(iterator, ast.Call) and isinstance(iterator.func, ast.Name)
            and iterator.func.id == "range" and not iterator.keywords
            and len(iterator.args) in (2, 3)):
        return False
    if len(iterator.args) == 3 and not (
        isinstance(iterator.args[2], ast.Constant) and iterator.args[2].value == 1
    ):
        return False
    width = iterator.args[0]
    if not (isinstance(width, ast.Name) or (
        isinstance(width, ast.Constant) and type(width.value) is int and width.value > 0
    )):
        return False
    index_name = loop.target.id
    if isinstance(width, ast.Name) and width.id == index_name:
        return False

    for position, statement in enumerate(loop.body):
        if not (isinstance(statement, ast.AugAssign) and isinstance(statement.target, ast.Name)
                and isinstance(statement.op, ast.Add)):
            continue
        accumulator = statement.target.id
        updates = [statement]
        if isinstance(statement.value, ast.BinOp) and isinstance(statement.value.op, ast.Sub):
            incoming, outgoing = statement.value.left, statement.value.right
        elif position + 1 < len(loop.body):
            removal = loop.body[position + 1]
            if not (isinstance(removal, ast.AugAssign) and isinstance(removal.op, ast.Sub)
                    and isinstance(removal.target, ast.Name) and removal.target.id == accumulator):
                continue
            incoming, outgoing = statement.value, removal.value
            updates.append(removal)
        else:
            continue
        if not (isinstance(incoming, ast.Subscript) and isinstance(incoming.value, ast.Name)
                and isinstance(incoming.slice, ast.Name) and incoming.slice.id == index_name
                and isinstance(outgoing, ast.Subscript) and isinstance(outgoing.value, ast.Name)
                and outgoing.value.id == incoming.value.id
                and isinstance(outgoing.slice, ast.BinOp) and isinstance(outgoing.slice.op, ast.Sub)
                and isinstance(outgoing.slice.left, ast.Name) and outgoing.slice.left.id == index_name
                and ast.dump(outgoing.slice.right) == ast.dump(width)):
            continue
        sequence = incoming.value.id
        stable_names = {index_name, sequence}
        if isinstance(width, ast.Name):
            stable_names.add(width.id)
        if any(writes_name(s, name) for s in loop.body for name in stable_names):
            continue
        if any(writes_name(s, accumulator) for s in loop.body if s not in updates):
            continue
        if has_initial_sum(preceding, accumulator, sequence, width):
            return True
    return False

def has_initial_sum(preceding: list, accumulator: str, sequence: str, width: ast.AST) -> bool:
    for statement in reversed(preceding):
        if writes_name(statement, accumulator):
            if not (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                    and isinstance(statement.targets[0], ast.Name)
                    and statement.targets[0].id == accumulator):
                return False
            value = statement.value
            if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                    and value.func.id == "sum" and len(value.args) == 1 and not value.keywords):
                return False
            window = value.args[0]
            return (
                isinstance(window, ast.Subscript) and isinstance(window.value, ast.Name)
                and window.value.id == sequence and isinstance(window.slice, ast.Slice)
                and (window.slice.lower is None or (
                    isinstance(window.slice.lower, ast.Constant) and window.slice.lower.value == 0
                ))
                and window.slice.step is None and window.slice.upper is not None
                and ast.dump(window.slice.upper) == ast.dump(width)
            )
        if writes_name(statement, sequence) or (
            isinstance(width, ast.Name) and writes_name(statement, width.id)
        ):
            return False
    return False

def writes_name(statement: ast.AST, name: str) -> bool:
    """Reject direct writes and conservatively treat receiver calls as mutations."""
    for node in ast.walk(statement):
        if isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, (ast.Store, ast.Del)):
            return True
        if (isinstance(node, ast.Subscript) and isinstance(node.ctx, (ast.Store, ast.Del))
                and isinstance(node.value, ast.Name) and node.value.id == name):
            return True
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name) and node.func.value.id == name):
            return True
    return False

