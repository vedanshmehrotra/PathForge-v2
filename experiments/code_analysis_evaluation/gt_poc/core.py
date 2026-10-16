"""Core POC primitives: normalization keys, signatures, skeleton, grouping.

READ-ONLY with respect to the frozen analyzer.  This module imports the shadow
pipeline only to *observe* it; it never changes detectors, techniques,
strategies, vocabulary, matching, or any production code.

Determinism: every function here is a pure function of its inputs.  No
timestamps, no randomness, no network, no database.
"""
import ast
import hashlib
import re

from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis

# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Analyzer access (read-only)
# ---------------------------------------------------------------------------

def analyze(code_text: str):
    """Run the frozen shadow pipeline read-only.

    Returns a dict with structural_facts / technique_evidence /
    strategy_evidence, or None when the code cannot be analysed.
    """
    return run_shadow_analysis(code_text, solution_groups=None)


def technique_ids(analysis) -> list:
    if not analysis:
        return []
    return sorted({t["technique_id"] for t in analysis.get("technique_evidence", [])})


def strategy_ids(analysis) -> list:
    if not analysis:
        return []
    return sorted({s["strategy_id"] for s in analysis.get("strategy_evidence", [])})


def fact_signature(analysis) -> list:
    """Name-free multiset of structural-fact types (sorted)."""
    if not analysis:
        return []
    counts = {}
    for f in analysis.get("structural_facts", []):
        counts[f["fact_type"]] = counts.get(f["fact_type"], 0) + 1
    return [f"{k}x{v}" for k, v in sorted(counts.items())]


def signature_class(tech_sig, strat_sig) -> str:
    """Primary grouping key: exact set of detected concepts (name-free)."""
    return "|".join(sorted(set(tech_sig) | set(strat_sig)))


# ---------------------------------------------------------------------------
# Normalization (comparison-only; NEVER written back to code_text)
# ---------------------------------------------------------------------------

def canonicalized_source(code_text: str) -> str:
    """Name-normalized AST rendering used for D2 (syntax-variant) detection.

    User identifiers (Name ids, argument names, function/class names) are
    renamed in first-occurrence order; attribute names, literals and operators
    are preserved.  This is a *comparison key only* — the stored code_text is
    never modified.
    """
    tree = ast.parse(code_text)
    mapping: dict = {}

    def rename(name: str) -> str:
        if name not in mapping:
            mapping[name] = f"v{len(mapping)}"
        return mapping[name]

    class _Rename(ast.NodeTransformer):
        def visit_Name(self, node):
            node.id = rename(node.id)
            return node

        def visit_arg(self, node):
            node.arg = rename(node.arg)
            return node

        def visit_FunctionDef(self, node):
            node.name = rename(node.name)
            self.generic_visit(node)
            return node

        def visit_AsyncFunctionDef(self, node):
            node.name = rename(node.name)
            self.generic_visit(node)
            return node

        def visit_ClassDef(self, node):
            node.name = rename(node.name)
            self.generic_visit(node)
            return node

    _Rename().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


# ---------------------------------------------------------------------------
# Skeleton (control-flow shape; user names abstracted, API names kept)
# ---------------------------------------------------------------------------

def _target(node) -> str:
    if node is None:
        return "-"
    if isinstance(node, ast.Name):
        return "Name"
    if isinstance(node, ast.Attribute):
        return "Attr(" + _sk(node.value) + ")"
    if isinstance(node, ast.Subscript):
        return "Sub(" + _sk(node.value) + ")"
    if isinstance(node, ast.Tuple):
        return "Tuple(" + ",".join(_target(e) for e in node.elts) + ")"
    return type(node).__name__


def _func_name(node) -> str:
    """API surface of a call: builtin/name or method name; else 'Call'."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return "Call"


def _sk(node) -> str:
    """Coarse canonical skeleton.  User identifiers -> 'Name'; API names kept."""
    if node is None:
        return "-"
    if isinstance(node, ast.Module):
        return "Module[" + ",".join(_sk(s) for s in node.body) + "]"
    if isinstance(node, ast.Name):
        return "Name"
    if isinstance(node, ast.Constant):
        return "Const"
    if isinstance(node, ast.Attribute):
        return "Attr(" + _sk(node.value) + ")"
    if isinstance(node, ast.Subscript):
        return "Sub(" + _sk(node.value) + ")"
    if isinstance(node, ast.Call):
        return "Call<" + _func_name(node.func) + ">(" + ",".join(_sk(a) for a in node.args) + ")"
    if isinstance(node, ast.BinOp):
        return type(node.op).__name__ + "(" + _sk(node.left) + "," + _sk(node.right) + ")"
    if isinstance(node, ast.UnaryOp):
        return type(node.op).__name__ + "(" + _sk(node.operand) + ")"
    if isinstance(node, ast.BoolOp):
        return type(node.op).__name__ + "(" + ",".join(_sk(v) for v in node.values) + ")"
    if isinstance(node, ast.Compare):
        ops = ",".join(type(o).__name__ for o in node.ops)
        return "Compare[" + ops + "](" + _sk(node.left) + "," + ",".join(_sk(c) for c in node.comparators) + ")"
    if isinstance(node, ast.IfExp):
        return "IfExp(" + _sk(node.test) + "?" + _sk(node.body) + ":" + _sk(node.orelse) + ")"
    if isinstance(node, ast.Lambda):
        return "Lambda[" + str(len(node.args.args)) + "](" + _sk(node.body) + ")"
    if isinstance(node, ast.List):
        return "List(" + ",".join(_sk(e) for e in node.elts) + ")"
    if isinstance(node, ast.Tuple):
        return "Tuple(" + ",".join(_sk(e) for e in node.elts) + ")"
    if isinstance(node, ast.Set):
        return "Set(" + ",".join(_sk(e) for e in node.elts) + ")"
    if isinstance(node, ast.Dict):
        return "Dict(" + ",".join(_sk(k) for k in node.keys) + "->" + ",".join(_sk(v) for v in node.values) + ")"
    if isinstance(node, ast.ListComp):
        return "ListComp(" + _sk(node.elt) + ")"
    if isinstance(node, ast.GeneratorExp):
        return "GenExp(" + _sk(node.elt) + ")"
    if isinstance(node, ast.FunctionDef):
        return "Def[" + str(len(node.args.args)) + "]{" + ",".join(_sk(s) for s in node.body) + "}"
    if isinstance(node, ast.ClassDef):
        return "Class{" + ",".join(_sk(s) for s in node.body) + "}"
    if isinstance(node, ast.For):
        return "For(" + _sk(node.iter) + "){" + ",".join(_sk(s) for s in node.body) + "}"
    if isinstance(node, ast.While):
        return "While(" + _sk(node.test) + "){" + ",".join(_sk(s) for s in node.body) + "}"
    if isinstance(node, ast.If):
        return ("If(" + _sk(node.test) + "){" + ",".join(_sk(s) for s in node.body)
                + "}else{" + ",".join(_sk(s) for s in node.orelse) + "}")
    if isinstance(node, ast.Assign):
        return "Assign(" + ",".join(_target(t) for t in node.targets) + "=" + _sk(node.value) + ")"
    if isinstance(node, ast.AnnAssign):
        return "AnnAssign(" + _target(node.target) + "=" + _sk(node.value) + ")"
    if isinstance(node, ast.AugAssign):
        return "Aug(" + _target(node.target) + type(node.op).__name__ + _sk(node.value) + ")"
    if isinstance(node, ast.Return):
        return "Return(" + _sk(node.value) + ")"
    if isinstance(node, ast.Expr):
        return "Expr(" + _sk(node.value) + ")"
    if isinstance(node, ast.Break):
        return "Break"
    if isinstance(node, ast.Continue):
        return "Continue"
    if isinstance(node, ast.Pass):
        return "Pass"
    if isinstance(node, ast.Raise):
        return "Raise"
    if isinstance(node, ast.Try):
        return "Try{" + ",".join(_sk(s) for s in node.body) + "}"
    if isinstance(node, ast.Import):
        return "Import"
    if isinstance(node, ast.ImportFrom):
        return "ImportFrom"
    return type(node).__name__


_TOKEN_RE = re.compile(r"[A-Za-z_]+|[0-9]+|\S")


def skeleton_tokens(skeleton: str) -> list:
    return _TOKEN_RE.findall(skeleton)


def skeleton_for(code_text: str) -> dict:
    tree = ast.parse(code_text)
    sk = _sk(tree)
    return {"skeleton": sk, "skeleton_tokens": skeleton_tokens(sk)}


def levenshtein(a: list, b: list) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def skeleton_distance(tokens_a: list, tokens_b: list) -> float:
    """Normalized token-level edit distance in [0, 1]."""
    longest = max(len(tokens_a), len(tokens_b))
    if longest == 0:
        return 0.0
    return levenshtein(tokens_a, tokens_b) / longest


# ---------------------------------------------------------------------------
# Deterministic family grouping (spec §8 steps 1-4)
# ---------------------------------------------------------------------------

from pathforge.ast_analysis.shadow.data_structures import EXTRACTOR_VERSION  # noqa: E402
from pathforge.ast_analysis.shadow.relations import RELATIONS_VERSION  # noqa: E402
from pathforge.ast_analysis.shadow.strategies import STRATEGY_VERSION  # noqa: E402

PIPELINE_VERSION = {
    "extractor": EXTRACTOR_VERSION,
    "relations": RELATIONS_VERSION,
    "strategy": STRATEGY_VERSION,
}


def build_families(problem_id: int, members: list, tau: float) -> list:
    """Group one problem's solutions into families.

    Steps (all deterministic):
      1. primary partition  — exact `signature_class` equality
      2. skeleton refinement — split when token distance >= tau
      3. tie-break          — none needed (no randomness in steps 1-2)
      4. anti-split guard   — implemented as connectivity: any D1/D2/D3 link
                              merges, so pure D2/D3 differences can never split
    """
    ordered = sorted(members, key=lambda m: m["solution_id"])
    n = len(ordered)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    links = []
    for i in range(n):
        for j in range(i + 1, n):
            a, b = ordered[i], ordered[j]
            same_class = a["signature_class"] == b["signature_class"]
            dist = skeleton_distance(a["skeleton_tokens"], b["skeleton_tokens"])
            if same_class and dist < tau:
                union(i, j)
                links.append({
                    "a": a["solution_id"], "b": b["solution_id"],
                    "skeleton_distance": round(dist, 4),
                })

    buckets = {}
    for i, m in enumerate(ordered):
        buckets.setdefault(find(i), []).append(i)

    groups = sorted(buckets.values(), key=lambda idxs: min(ordered[k]["solution_id"] for k in idxs))
    families = []
    for k, idxs in enumerate(groups, start=1):
        mem = [ordered[i] for i in idxs]
        canon = min(mem, key=lambda m: m["solution_id"])
        intra = [
            round(skeleton_distance(a["skeleton_tokens"], b["skeleton_tokens"]), 4)
            for ai, a in enumerate(mem) for b in mem[ai + 1:]
        ]
        families.append({
            "problem_id": problem_id,
            "family_key": f"lc{problem_id}_fam{k}",
            "members": [m["solution_id"] for m in mem],
            "canonical_solution_id": canon["solution_id"],
            "technique_signature": sorted({t for m in mem for t in m["technique_signature"]}),
            "strategy_signature": sorted({s for m in mem for s in m["strategy_signature"]}),
            "signature_class": canon["signature_class"],
            "max_intra_skeleton_distance": max(intra) if intra else 0.0,
            "member_count": len(mem),
        })
    return families
