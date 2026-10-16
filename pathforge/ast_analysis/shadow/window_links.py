"""Scoped window observations; no technique, confidence, or authority policy."""
import ast
import copy

from pathforge.ast_analysis.shadow.data_structures import StructuralFact
from src.ast_detection.window_structure import (
    boundary_window_link, has_offset_window_update, maintenance_events,
    range_driver, scope_nodes, same, name, unit_advance, index_read,
    state_updates_linked, linked_trailing_advance, writes_name,
)


def _ref(node):
    return f"{node.lineno}:{node.col_offset}"


def _initial_zero(preceding, variable):
    for statement in reversed(preceding):
        if any(isinstance(n, ast.Name) and n.id == variable and isinstance(n.ctx, (ast.Store, ast.Del))
               for n in scope_nodes([statement])):
            return (isinstance(statement, ast.Assign) and len(statement.targets) == 1 and name(statement.targets[0], variable)
                    and isinstance(statement.value, ast.Constant) and statement.value.value == 0)
    return False


def _variable_link(loop, lead, preceding):
    events = maintenance_events(loop.body)
    for incoming in events:
        if not name(incoming["index"], lead):
            continue
        if (not state_updates_linked(loop.body, incoming["state"], incoming["sequence"], events)
                or any(writes_name(s, incoming["sequence"]) for s in loop.body)):
            continue
        for outgoing in events:
            index = outgoing["index"]
            if (incoming["direction"] != -outgoing["direction"] or incoming["state"] != outgoing["state"]
                    or incoming["sequence"] != outgoing["sequence"]
                    or not isinstance(index, ast.Name) or index.id == lead or not _initial_zero(preceding, index.id)):
                continue
            for guard in outgoing["controls"]:
                if (not linked_trailing_advance(loop.body, guard, index.id, outgoing["node"])
                        or not (any(name(n, incoming["state"]) for n in scope_nodes([guard.test]))
                                or {lead, index.id} <= {n.id for n in scope_nodes([guard.test]) if isinstance(n, ast.Name)})):
                    continue
                return {"kind": "variable", "state": incoming["state"], "sequence": incoming["sequence"],
                        "leading": lead, "trailing": index.id, "incoming_ref": _ref(incoming["node"]),
                        "outgoing_ref": _ref(outgoing["node"]), "guard_ref": _ref(guard)}
    return None


def _jump_link(loop, lead, preceding):
    aliases = {}
    for position, statement in enumerate(loop.body):
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
            aliases[statement.targets[0].id] = statement.value
        if not isinstance(statement, ast.If):
            continue
        guards = statement.test.values if isinstance(statement.test, ast.BoolOp) and isinstance(statement.test.op, ast.And) else [statement.test]
        for membership in guards:
            if not (isinstance(membership, ast.Compare) and len(membership.ops) == 1 and isinstance(membership.ops[0], ast.In)
                    and isinstance(membership.comparators[0], ast.Name)):
                continue
            item = membership.left
            read = index_read(item, aliases)
            if not read or not name(read[1], lead):
                continue
            if any(writes_name(s, read[0]) for s in loop.body):
                continue
            mapping = membership.comparators[0].id
            for update in statement.body:
                if not (isinstance(update, ast.Assign) and len(update.targets) == 1 and isinstance(update.targets[0], ast.Name)):
                    continue
                trailing = update.targets[0].id
                if trailing == lead or not _initial_zero(preceding, trailing):
                    continue
                value = update.value
                protected = False
                if (isinstance(value, ast.Call) and name(value.func, "max") and len(value.args) == 2 and not value.keywords
                        and name(value.args[0], trailing)):
                    value = value.args[1]
                    protected = True
                if not (isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add)
                        and isinstance(value.right, ast.Constant) and type(value.right.value) is int and value.right.value == 1
                        and isinstance(value.left, ast.Subscript) and name(value.left.value, mapping) and same(value.left.slice, item)):
                    continue
                if not protected:
                    protected = any(isinstance(g, ast.Compare) and len(g.ops) == 1 and isinstance(g.ops[0], ast.GtE)
                                    and same(g.left, value.left) and name(g.comparators[0], trailing) for g in guards)
                if not protected:
                    continue
                writes = [s for s in loop.body[position + 1:] if isinstance(s, ast.Assign) and len(s.targets) == 1
                          and isinstance(s.targets[0], ast.Subscript) and name(s.targets[0].value, mapping)
                          and same(s.targets[0].slice, item) and name(s.value, lead)]
                if not writes:
                    continue
                if (any(writes_name(s, trailing) or writes_name(s, mapping) for s in loop.body if s is not statement and s not in writes)
                        or any(writes_name(s, trailing) or writes_name(s, mapping) for s in statement.body if s is not update)
                        or any(writes_name(s, trailing) or writes_name(s, mapping) for s in statement.orelse)):
                    continue
                extent = any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Sub)
                             and name(n.left, lead) and name(n.right, trailing) for n in scope_nodes(loop.body))
                if extent:
                    return {"kind": "jump", "sequence": read[0], "mapping": mapping, "leading": lead,
                            "trailing": trailing, "guard_ref": _ref(statement), "update_ref": _ref(update),
                            "mapping_write_ref": _ref(writes[0])}
    return None


def _offset_expression(value, lead, width, outgoing=False):
    """Same element expression at the incoming/outgoing positions; no calls."""
    normalized = copy.deepcopy(value)
    sequences = set()
    reads = [n for n in ast.walk(normalized) if isinstance(n, ast.Subscript)]
    if not reads or any(isinstance(n, (ast.Call, ast.Lambda, ast.NamedExpr, ast.GeneratorExp)) for n in ast.walk(normalized)):
        return None
    for read in reads:
        if not isinstance(read.value, ast.Name):
            return None
        index = read.slice
        valid = (isinstance(index, ast.BinOp) and isinstance(index.op, ast.Sub) and name(index.left, lead)
                 and same(index.right, width)) if outgoing else name(index, lead)
        if not valid:
            return None
        sequences.add(read.value.id)
        read.slice = ast.Constant(value="window_position")
    return ast.dump(normalized, include_attributes=False), sequences


def _initialized_offset(before, state, sequences, width, incoming, lead):
    for position in range(len(before) - 1, -1, -1):
        statement = before[position]
        if any(writes_name(statement, v) for v in sequences | ({width.id} if isinstance(width, ast.Name) else set())):
            return None
        if not writes_name(statement, state):
            continue
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and name(statement.targets[0], state):
            value = statement.value
            if not (isinstance(value, ast.Call) and name(value.func, "sum") and len(value.args) == 1 and not value.keywords):
                return None
            argument = value.args[0]
            if len(sequences) == 1 and isinstance(argument, ast.Subscript):
                if isinstance(argument.value, ast.Name) and argument.value.id in sequences and isinstance(argument.slice, ast.Slice):
                    slice_ = argument.slice
                    if (slice_.lower is None or isinstance(slice_.lower, ast.Constant) and slice_.lower.value == 0) and slice_.step is None and slice_.upper is not None and same(slice_.upper, width):
                        return _ref(statement)
            # Weighted maintenance may initialize from a bounded zip fold.
            # This observes its fixed input region, not correctness of its cost.
            if isinstance(argument, ast.GeneratorExp) and len(argument.generators) == 1:
                iteration = argument.generators[0]
                iterator = iteration.iter
                if isinstance(iterator, ast.Call) and name(iterator.func, "zip") and not iterator.keywords and not iteration.ifs and not iteration.is_async:
                    slices = iterator.args
                    bound = {n.id for n in ast.walk(iteration.target) if isinstance(n, ast.Name)}
                    used = {n.id for n in ast.walk(argument.elt) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
                    if (bound & used and not any(isinstance(n, (ast.Call, ast.NamedExpr)) for n in ast.walk(argument.elt))
                            and len(slices) == len(sequences) and all(isinstance(s, ast.Subscript) and isinstance(s.value, ast.Name)
                            and s.value.id in sequences and isinstance(s.slice, ast.Slice) and s.slice.lower is None
                            and s.slice.step is None and s.slice.upper is not None and same(s.slice.upper, width) for s in slices)
                            and {s.value.id for s in slices} == sequences):
                        return _ref(statement)
            return None
        if isinstance(statement, ast.For) and isinstance(statement.target, ast.Name) and len(statement.body) == 1 and not statement.orelse:
            iterator = statement.iter
            update = statement.body[0]
            if (isinstance(iterator, ast.Call) and name(iterator.func, "range") and len(iterator.args) == 1 and not iterator.keywords
                    and same(iterator.args[0], width) and isinstance(update, ast.AugAssign) and name(update.target, state)
                    and isinstance(update.op, ast.Add) and _initial_zero(before[:position], state)):
                initial = _offset_expression(update.value, statement.target.id, width)
                expected = _offset_expression(incoming, lead, width)
                if initial and expected and initial == expected:
                    return _ref(statement)
        return None
    return None


def _extended_offset_link(loop, preceding):
    """Preserve reviewed assignment, prefix-fold, weighted and while forms."""
    body = loop.body
    if isinstance(loop, ast.For):
        lead = range_driver(loop)
        if not lead or len(loop.iter.args) < 2:
            return None
        width = loop.iter.args[0]
    else:
        test = loop.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Lt) and isinstance(test.left, ast.Name)):
            return None
        lead = test.left.id
        advances = [s for s in body if unit_advance(s, lead)]
        if len(advances) != 1 or any(writes_name(s, lead) for s in body if s not in advances):
            return None
        start = next((s for s in reversed(preceding) if writes_name(s, lead)), None)
        if not (isinstance(start, ast.Assign) and len(start.targets) == 1 and name(start.targets[0], lead)):
            return None
        width = start.value
    if not (isinstance(width, ast.Name) and width.id != lead or isinstance(width, ast.Constant) and type(width.value) is int and width.value > 0):
        return None
    for position, statement in enumerate(body):
        updates = [statement]
        if isinstance(statement, ast.AugAssign) and isinstance(statement.op, ast.Add) and isinstance(statement.target, ast.Name):
            state, value = statement.target.id, statement.value
            if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Sub):
                incoming, outgoing = value.left, value.right
            elif position + 1 < len(body) and isinstance(body[position + 1], ast.AugAssign) and isinstance(body[position + 1].op, ast.Sub) and name(body[position + 1].target, state):
                updates.append(body[position + 1])
                incoming, outgoing = value, updates[-1].value
            else:
                continue
        elif isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
            state, value = statement.targets[0].id, statement.value
            if not (isinstance(value, ast.BinOp) and isinstance(value.op, ast.Sub) and isinstance(value.left, ast.BinOp)
                    and isinstance(value.left.op, ast.Add) and name(value.left.left, state)):
                continue
            incoming, outgoing = value.left.right, value.right
        else:
            continue
        positive, negative = _offset_expression(incoming, lead, width), _offset_expression(outgoing, lead, width, outgoing=True)
        if not positive or positive != negative:
            continue
        sequences = positive[1]
        stable = {n.id for n in ast.walk(incoming) if isinstance(n, ast.Name)} - {lead}
        stable |= sequences | ({width.id} if isinstance(width, ast.Name) else set())
        if any(writes_name(s, v) for v in stable for s in body) or any(writes_name(s, state) for s in body if s not in updates):
            continue
        initialized = _initialized_offset(preceding, state, sequences, width, incoming, lead)
        if initialized:
            return {"kind": "fixed_offset", "leading": lead, "state": state, "sequences": sorted(sequences),
                    "width": ast.unparse(width), "initial_ref": initialized, "update_refs": [_ref(s) for s in updates]}
    return None


def extract_window_links(tree):
    preceding = {}
    for parent in ast.walk(tree):
        for _, children in ast.iter_fields(parent):
            if isinstance(children, list):
                for i, child in enumerate(children):
                    if isinstance(child, (ast.For, ast.While)):
                        preceding[child] = children[:i]
    result = []
    for loop, before in preceding.items():
        if isinstance(loop, ast.While):
            link = _extended_offset_link(loop, before)
            if link:
                result.append(StructuralFact(fact_type="window_maintenance", ast_ref=_ref(loop), attributes={"window": link}))
            continue
        lead = range_driver(loop)
        if lead is None:
            continue
        if has_offset_window_update(loop, before):
            link = {"kind": "fixed_offset", "leading": lead}
        else:
            link = (boundary_window_link(loop, before) or _variable_link(loop, lead, before)
                    or _jump_link(loop, lead, before) or _extended_offset_link(loop, before))
        if link:
            # Opaque to generic top-level variable scans in existing techniques.
            result.append(StructuralFact(fact_type="window_maintenance", ast_ref=_ref(loop), attributes={"window": link}))
    return result
