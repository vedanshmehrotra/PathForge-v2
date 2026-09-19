"""Shared relational evidence layer (M2).

Computes reusable variable relationships once per submission from the parsed
AST. This is NOT a CFG/SSA system: no dominators, no path sensitivity, no
reaching definitions. It is the smallest normalized layer that removes the
need for each technique detector to re-implement its own hand-rolled
relational joins over fact attributes — the mechanism the architecture
survey identified as the third brittleness class.

Design constraints (from the architecture survey):
- Deterministic: same code -> same relations.
- Additive: existing fact extraction and outputs are untouched.
- Relation granularity is the enclosing loop: ``updated_in_loop`` lists the
  loop kind(s) a variable is updated in, matching the evidence needs of the
  current technique layer without inventing loop-flow machinery.
- Consumption is optional and backward-compatible: techniques that have not
  migrated keep their fact-attribute logic (byte-identical behavior).
"""
import ast
from dataclasses import dataclass, field


RELATIONS_VERSION = "1.1.0"


@dataclass
class SubmissionRelations:
    """Reusable structural relationships computed once per submission."""

    #: variable -> loop kinds it is updated in ({"for", "while"})
    updated_in_loop: dict = field(default_factory=dict)

    #: variables that appear as a subscript index (arr[i], arr[i - 1], ...)
    used_as_subscript_index: set = field(default_factory=set)

    #: variables that are used (read) anywhere
    used_anywhere: set = field(default_factory=set)

    #: variables that are assigned/written anywhere
    assigned_anywhere: set = field(default_factory=set)

    #: variable -> sorted list of used-by variable names (def -> users)
    def_use_pairs: dict = field(default_factory=dict)

    #: variable -> set of collection operations performed on it
    #: {"append", "pop", "popleft", "pop(0)", "heappush", "heappop", "popleft_tuple", "pop(0)_tuple"}
    collection_ops: dict = field(default_factory=dict)

    #: variables that a for-loop directly iterates over (for x in X)
    iterated_in_for: set = field(default_factory=set)

    #: structure name -> {"indexed_write", "append"}
    #:
    #: Records container structures that receive a **self-referential
    #: cumulative update inside a loop body**: an indexed write whose value
    #: combines exactly one read of the same structure with an external
    #: value (``freq[x] = freq.get(x, 0) + 1``, ``out[i + 1] = out[i] + v``)
    #: or an append whose argument combines exactly one read of the same
    #: structure (``prefix.append(prefix[-1] + x)``). Loop-scoped like
    #: ``updated_in_loop``: a self-referential update outside any loop is
    #: deliberately not recorded, so this relation cannot turn one-shot
    #: initialization into accumulation evidence.
    self_referential_updates: dict = field(default_factory=dict)


def build_relations(ast_root: ast.AST) -> SubmissionRelations:
    """Build the relational-evidence bundle for a submission.

    One pass over the AST collects all relation kinds. No relation requires
    flow-sensitive analysis: each is a localized syntactic observation that
    is stable across statement forms (Assign / AnnAssign / AugAssign /
    tuple-unpack), which is precisely the normalization M1 introduced at
    the fact layer.
    """
    rel = SubmissionRelations()
    _collect_name_usage(ast_root, rel)
    _collect_collection_ops(ast_root, rel)
    _collect_loop_updates(ast_root, rel)
    _collect_for_iteration(ast_root, rel)
    return rel


# ----------------------------------------------------------------
# Name usage: defs, uses, subscript-index participation, def-use pairs
# ----------------------------------------------------------------

def _walk_name_contexts(node: ast.AST):
    """Yield (name, is_load, used_by) for every Name in the subtree.

    ``used_by`` is the innermost enclosing assignment target when the Name
    sits in an assignment RHS, else ``None`` — enough granularity for
    def-use pairs without flow analysis.
    """
    for parent in ast.walk(node):
        if not isinstance(parent, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            continue
        if isinstance(parent, ast.AugAssign) and isinstance(parent.target, ast.Name):
            # AugAssign is both a use and a def of its target
            yield (parent.target.id, True, None)
        targets = _assign_targets(parent)
        rhs_names = {c.id for c in ast.walk(parent.value) if isinstance(c, ast.Name)} if parent.value is not None else set()
        for t in targets:
            if isinstance(t, ast.Name):
                # x = ...  (or augmented self-update): the RHS uses relate to this def
                for rhs in rhs_names:
                    yield (rhs, True, t.id)
                if isinstance(parent, ast.AugAssign):
                    yield (t.id, True, None)
                yield (t.id, False, None)
            elif isinstance(t, ast.Tuple):
                for elt in t.elts:
                    if isinstance(elt, ast.Name):
                        for rhs in rhs_names:
                            yield (rhs, True, elt.id)
                        yield (elt.id, False, None)
        # Names in the RHS that were not covered by target-specific yields
        if parent.value is not None:
            for child in ast.walk(parent.value):
                if isinstance(child, ast.Name) and child.id not in rhs_names:
                    continue
                if isinstance(child, ast.Name):
                    yield (child.id, True, None)


def _collect_name_usage(node: ast.AST, rel: SubmissionRelations) -> None:
    """Collect assigned/used sets, subscript-index participation, def-use pairs.

    Two walks:
    - A generic walk for uses (Name in Load context), subscript indices,
      and plain assignment targets (including tuple unpacking).
    - The context walk for def-use pairs, whose yields must not double-count.
    """
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            if isinstance(n.ctx, ast.Load):
                rel.used_anywhere.add(n.id)
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                for name_node in ast.walk(t):
                    if isinstance(name_node, ast.Name):
                        rel.assigned_anywhere.add(name_node.id)
        elif isinstance(n, ast.AnnAssign):
            if isinstance(n.target, ast.Name):
                rel.assigned_anywhere.add(n.target.id)
        elif isinstance(n, ast.AugAssign):
            if isinstance(n.target, ast.Name):
                rel.assigned_anywhere.add(n.target.id)
                rel.used_anywhere.add(n.target.id)
        elif isinstance(n, ast.Subscript):
            # Index participation: the slice names (arr[i], arr[i-1], m[i][j])
            for child in ast.walk(n.slice):
                if isinstance(child, ast.Name):
                    rel.used_as_subscript_index.add(child.id)

    # Def-use pairs from the context walk
    for name, _is_load, used_by in _walk_name_contexts(node):
        if used_by:
            users = rel.def_use_pairs.setdefault(name, set())
            users.add(used_by)


def _assign_targets(node) -> list:
    """Normalize assignment targets (Assign list / AnnAssign / AugAssign single)."""
    if isinstance(node, ast.Assign):
        return list(node.targets)
    if isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        return [node.target]
    return []


# ----------------------------------------------------------------
# Collection operations per variable
# ----------------------------------------------------------------

def _record_op(rel: SubmissionRelations, var: str, op: str) -> None:
    rel.collection_ops.setdefault(var, set()).add(op)


def _collect_collection_ops(node: ast.AST, rel: SubmissionRelations) -> None:
    """Record append / pop / popleft / heappush / heappop per variable.

    Position matters and is preserved as part of the operation token:
    ``pop`` (stack end), ``popleft`` (queue front), ``pop(0)`` (list queue
    front). Tuple-unpack consumption (``r, c = q.popleft()``) is the same
    operation on the same variable — only the statement wrapper differs,
    which is the M1 normalization.
    """
    for n in ast.walk(node):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
            continue
        method = n.func.attr
        # heapq.heappush(heap, x) / heapq.heappop(heap): the receiver is the
        # heapq module — the operated-on collection is the first argument.
        if method in ("heappush", "heappop"):
            if n.args and isinstance(n.args[0], ast.Name):
                _record_op(rel, n.args[0].id, method)
            continue
        recv = n.func.value
        if isinstance(recv, ast.Name):
            if method == "append":
                _record_op(rel, recv.id, "append")
            elif method == "pop":
                if not n.args and not n.keywords:
                    _record_op(rel, recv.id, "pop")
                elif (
                    n.args
                    and isinstance(n.args[0], ast.Constant)
                    and n.args[0].value == 0
                ):
                    _record_op(rel, recv.id, "pop(0)")
                else:
                    _record_op(rel, recv.id, "pop(n)")
            elif method == "popleft":
                _record_op(rel, recv.id, "popleft")
        elif isinstance(recv, ast.Attribute) and method == "append":
            # Attribute-backed container (``self.prefix.append(...)``): the
            # structure is tracked by its attribute name, matching how the
            # self-referential-update relation keys attribute bases. Only
            # appends are recorded here; attribute pop/popleft has no
            # consumer and different semantics.
            _record_op(rel, recv.attr, "append")


# ----------------------------------------------------------------
# Loop-scoped updates
# ----------------------------------------------------------------

def _collect_loop_updates(ast_root: ast.AST, rel: SubmissionRelations) -> None:
    """Record which variables are updated inside for/while loop bodies.

    Scoped to the nearest enclosing loop, not transitively nested ones —
    matching the evidence granularity the technique layer needs ("this
    accumulator is updated in a for loop") without loop-flow machinery.

    Appending to a container (``x.append(...)``) is an update of ``x``, so
    append receivers are recorded too; without this a container accumulated
    via ``append`` was invisible to loop-membership checks.
    """
    for loop in ast.walk(ast_root):
        if isinstance(loop, (ast.For, ast.While)):
            kind = "for" if isinstance(loop, ast.For) else "while"
            for stmt in loop.body:
                for n in ast.walk(stmt):
                    updated = _updated_names(n)
                    for name in updated:
                        rel.updated_in_loop.setdefault(name, set()).add(kind)
                    _record_append_receiver(n, kind, rel)
                    _record_self_referential_update(n, rel)


def _updated_names(n: ast.AST) -> set:
    """Names updated by this statement node (any assignment family form).

    A subscript target updates its *container structure* — that is how a
    plain Name base is already handled (``freq[k] = v`` records ``freq``
    via the walk). Attribute bases (``self.nums[k] = v``) walk to the
    ``self`` Name, so the attribute name is added explicitly to keep the
    structure keying consistent for attribute-backed containers.
    """
    if isinstance(n, ast.Assign):
        names = set()
        for t in n.targets:
            for child in ast.walk(t):
                if isinstance(child, ast.Name):
                    names.add(child.id)
            if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Attribute):
                names.add(t.value.attr)
        return names
    if isinstance(n, (ast.AnnAssign, ast.AugAssign)):
        if isinstance(n.target, ast.Name):
            return {n.target.id}
        if isinstance(n.target, ast.Subscript) and isinstance(
            n.target.value, ast.Attribute
        ):
            return {n.target.value.attr}
    return set()


# ----------------------------------------------------------------
# Same-structure self-referential container updates (loop-scoped)
# ----------------------------------------------------------------

def container_base(node: ast.AST) -> "str | None":
    """Base name of a container expression: ``freq`` / ``self.freq`` -> "freq".

    Returns the innermost attribute name for attribute chains, so a method
    call receiver (``freq.get``) and a subscript base (``freq[x]``) resolve
    to the same structure key. Anything else (calls, binops, nested
    subscripts like ``grid[r][c]``) has no tracked container base.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def count_structure_reads(node: ast.AST, structure: str) -> int:
    """Count reads of ``structure`` in an expression subtree.

    A read site is a subscript of the structure (``freq[x]``,
    ``self.prefix[-1]``) or a method-call receiver (``freq.get(...)``).
    Matching stops at the first matched site (no descent into it), so
    ``freq.get(x, 0)`` counts as exactly one read rather than two.
    """
    if node is None:
        return 0
    if isinstance(node, ast.Subscript) and container_base(node.value) == structure:
        return 1
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and container_base(node.func.value) == structure
    ):
        return 1
    if isinstance(node, ast.Attribute) and container_base(node) == structure:
        return 1
    total = 0
    for child in ast.iter_child_nodes(node):
        total += count_structure_reads(child, structure)
    return total


def _record_append_receiver(n: ast.AST, kind: str, rel: SubmissionRelations) -> None:
    """Record ``x.append(...)`` receivers as loop-body updates of ``x``."""
    if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
        return
    if n.func.attr != "append":
        return
    base = container_base(n.func.value)
    if base:
        rel.updated_in_loop.setdefault(base, set()).add(kind)


def _record_self_referential_update(n: ast.AST, rel: SubmissionRelations) -> None:
    """Record loop-body self-referential cumulative container updates.

    Two structural forms, both requiring the value to combine **exactly
    one** read of the same structure with an external value via Add/Sub:

    - indexed write: ``freq[x] = freq.get(x, 0) + 1`` (Assign/AnnAssign with
      a subscript target); a second self-read (``dp[i-1] + dp[i-2]``) means
      the value is composed of the structure itself — table filling, not
      accumulation — and is deliberately not recorded;
    - append: ``prefix.append(prefix[-1] + x)``; a non-BinOp argument
      (``result.append(x)``, ``copy.append(src[-1])``) is not cumulative
      and is deliberately not recorded.

    Augmented subscript writes (``cnt[x] += 1``) are NOT recorded here:
    that form belongs to the counting vocabulary, not accumulation.
    """
    if isinstance(n, (ast.Assign, ast.AnnAssign)) and n.value is not None:
        if not isinstance(n.value, ast.BinOp) or not isinstance(
            n.value.op, (ast.Add, ast.Sub)
        ):
            return
        for target in _assign_targets(n):
            if not isinstance(target, ast.Subscript):
                continue
            structure = container_base(target.value)
            if not structure:
                continue
            if count_structure_reads(n.value, structure) == 1:
                rel.self_referential_updates.setdefault(structure, set()).add(
                    "indexed_write"
                )
        return
    if (
        isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "append"
        and len(n.args) == 1
        and isinstance(n.args[0], ast.BinOp)
        and isinstance(n.args[0].op, (ast.Add, ast.Sub))
    ):
        structure = container_base(n.func.value)
        if structure and count_structure_reads(n.args[0], structure) == 1:
            rel.self_referential_updates.setdefault(structure, set()).add("append")


# ----------------------------------------------------------------
# For-loop iteration
# ----------------------------------------------------------------

def _collect_for_iteration(ast_root: ast.AST, rel: SubmissionRelations) -> None:
    """Record collections directly iterated by for-loops (for x in X)."""
    for loop in ast.walk(ast_root):
        if isinstance(loop, ast.For) and isinstance(loop.iter, ast.Name):
            rel.iterated_in_for.add(loop.iter.id)
