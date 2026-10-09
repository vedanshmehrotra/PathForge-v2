"""Functional DSU regressions using real detection and problem-aware matching."""

import ast
from pathlib import Path
import socket

import pytest

from pathforge.api.services.analysis import run_analysis
from src.ast_detection.detectors.union_find import UnionFindDetector


def _reviewed_classic():
    corpus = Path(__file__).resolve().parents[3] / (
        "pathforge/ast_analysis/shadow/tests/evaluation_corpus.py"
    )
    for node in ast.walk(ast.parse(corpus.read_text(encoding="utf-8"))):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "add"
                and ast.literal_eval(node.args[0]) == "uf_classic"):
            return ast.literal_eval(node.args[1])
    raise AssertionError("Reviewed uf_classic source is missing")


CLASSIC = _reviewed_classic()
GROUPS = [{"patterns": ["union_find"]}, {"patterns": ["binary_search_standard"]}]

RECURSIVE = """
def representative(forest, vertex):
    if forest[vertex] != vertex:
        forest[vertex] = representative(forest, forest[vertex])
    return forest[vertex]

def link(forest, first, second):
    a = representative(forest, first)
    b = representative(forest, second)
    if a != b:
        forest[b] = a
"""


@pytest.fixture(autouse=True)
def isolated_engines(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("DSU tests must not connect to databases or external services")

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setattr("psycopg2.connect", forbidden)
    monkeypatch.setattr("psycopg2.pool.ThreadedConnectionPool", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def _assert_dsu(code, kind="find_iterative"):
    direct = UnionFindDetector().detect(ast.parse(code))
    actual = run_analysis(code, accepted_solution_groups=GROUPS)
    assert "error" not in actual
    match = actual["match_result"]
    assert (direct.detected, match["match_result"], match["matched_groups"]) == (
        True, "FULL_MATCH", [0],
    )
    assert direct.pattern_id == "union_find"
    assert {item.type for item in direct.evidence} == {"parent_array", kind, "union_operation"}
    assert 0 < direct.confidence <= 1
    assert any(p["pattern_id"] == "union_find" for p in actual["ast"]["detected_patterns"])
    return direct


def test_reviewed_classic_reaches_real_matching():
    # Root traversal/path halving and calls on the same parent parameter lead
    # to a write linking the two returned representatives, with optional rank.
    _assert_dsu(CLASSIC)


def test_recursive_functional_dsu_without_rank():
    _assert_dsu(RECURSIVE, "find_recursive")


def test_iterative_representative_traversal_without_compression_or_rank():
    code = """
def root(forest, vertex):
    while forest[vertex] != vertex:
        vertex = forest[vertex]
    return vertex

def link(forest, first, second):
    a, b = root(forest, first), root(forest, second)
    forest[b] = a
"""
    _assert_dsu(code)


@pytest.mark.parametrize("code,kind", [(CLASSIC, "find_iterative"), (RECURSIVE, "find_recursive")])
def test_equivalent_renaming_preserves_detection_and_confidence(code, kind):
    aliases = {"find": "leader", "representative": "leader", "union": "connect", "link": "connect",
               "parent": "links", "forest": "links", "rank": "heights", "x": "node_a", "y": "node_b",
               "vertex": "node", "first": "node_a", "second": "node_b", "px": "root_a", "py": "root_b",
               "a": "root_a", "b": "root_b"}
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            node.id = aliases.get(node.id, node.id)
        elif isinstance(node, ast.arg):
            node.arg = aliases.get(node.arg, node.arg)
        elif isinstance(node, ast.FunctionDef):
            node.name = aliases.get(node.name, node.name)
    original = _assert_dsu(code, kind)
    renamed = _assert_dsu(ast.unparse(tree), kind)
    assert renamed.confidence == original.confidence


def test_parameter_order_is_bound_to_actual_call_arguments():
    code = RECURSIVE.replace("representative(forest, vertex)", "representative(vertex, forest)").replace(
        "representative(forest, forest[vertex])", "representative(forest[vertex], forest)"
    ).replace("representative(forest, first)", "representative(first, forest)").replace(
        "representative(forest, second)", "representative(second, forest)"
    )
    _assert_dsu(code, "find_recursive")


def test_keyword_arguments_bind_the_same_parent_and_vertex_roles():
    code = RECURSIVE.replace("representative(forest, first)", "representative(vertex=first, forest=forest)").replace(
        "representative(forest, second)", "representative(forest=forest, vertex=second)"
    )
    _assert_dsu(code, "find_recursive")


def test_shadowing_in_an_unrelated_function_does_not_rebind_module_lookup():
    _assert_dsu(RECURSIVE + "\ndef unrelated(representative):\n    return representative\n", "find_recursive")


LOOKUP = RECURSIVE.split("def link")[0]


def _with_union(body, signature="forest, first, second"):
    return LOOKUP + f"def link({signature}):\n" + "\n".join("    " + line for line in body.splitlines()) + "\n"


NEGATIVES = {
    "lookup_alone": LOOKUP,
    "arbitrary_parent_writes": "def link(parent, x, y):\n    parent[y] = x\n",
    "parent_traversal_only": "def root(parent, x):\n    while parent[x] != x:\n        x = parent[x]\n    return x\n",
    "generic_recursion": "def find(x):\n    return find(x - 1) if x else 0\n\ndef union(parent, x, y):\n    parent[y] = find(x)\n",
    "disconnected_callee": _with_union("a = unrelated(forest, first)\nb = unrelated(forest, second)\nforest[b] = a"),
    "different_parent_structures": _with_union(
        "a = representative(forest, first)\nb = representative(other, second)\nforest[b] = a",
        "forest, other, first, second",
    ),
    "raw_input_index": _with_union("a = representative(forest, first)\nb = representative(forest, second)\nforest[second] = a"),
    "raw_input_value": _with_union("a = representative(forest, first)\nb = representative(forest, second)\nforest[b] = first"),
    "same_input_twice": _with_union("a = representative(forest, first)\nb = representative(forest, first)\nforest[b] = a"),
    "different_write_structure": _with_union(
        "a = representative(forest, first)\nb = representative(forest, second)\nother[b] = a",
        "forest, other, first, second",
    ),
    "overwritten_root": _with_union("a = representative(forest, first)\nb = representative(forest, second)\na = 0\nforest[b] = a"),
    "overwritten_parent": _with_union(
        "a = representative(forest, first)\nb = representative(forest, second)\nforest = other\nforest[b] = a",
        "forest, other, first, second",
    ),
    "helper_parameter_shadow": _with_union(
        "a = representative(forest, first)\nb = representative(forest, second)\nforest[b] = a",
        "forest, first, second, representative",
    ),
    "helper_local_shadow": _with_union("representative = unrelated\na = representative(forest, first)\nb = representative(forest, second)\nforest[b] = a"),
    "conditional_lookup_not_established": _with_union(
        "if ready:\n    a = representative(forest, first)\n    b = representative(forest, second)\nforest[b] = a"
    ),
    "nonrepresentative_return": RECURSIVE.replace("return forest[vertex]", "return 0"),
    "unrelated_lookup_guard": RECURSIVE.replace("if forest[vertex] != vertex:", "if ready:"),
    "disconnected_scopes": "def outer():\n" + "\n".join("    " + line for line in LOOKUP.splitlines()) +
        "\n" + _with_union("a = representative(forest, first)\nb = representative(forest, second)\nforest[b] = a")[len(LOOKUP):],
    "helper_module_rebound": LOOKUP + "representative = unrelated\n" +
        _with_union("a = representative(forest, first)\nb = representative(forest, second)\nforest[b] = a")[len(LOOKUP):],
    "root_written_in_condition": _with_union(
        "a = representative(forest, first)\nb = representative(forest, second)\nif (a := 0):\n    pass\nforest[b] = a"
    ),
    "root_list_assignment": _with_union(
        "a = representative(forest, first)\nb = representative(forest, second)\n[a, b] = [0, 1]\nforest[b] = a"
    ),
    "mismatched_tuple_assignment": _with_union(
        "a = representative(forest, first)\nb = representative(forest, second)\na, b = (0,)\nforest[b] = a"
    ),
    "local_function_replaces_root": _with_union(
        "a = representative(forest, first)\nb = representative(forest, second)\ndef a():\n    return 0\nforest[b] = a"
    ),
    "import_replaces_root": _with_union(
        "a = representative(forest, first)\nb = representative(forest, second)\nfrom other import a\nforest[b] = a"
    ),
    "recursive_callee_is_parent_parameter": RECURSIVE.replace("forest", "representative"),
    "recursive_call_uses_other_parent": RECURSIVE.replace(
        "representative(forest, forest[vertex])", "representative(other, forest[vertex])"
    ),
}


@pytest.mark.parametrize("name,code", NEGATIVES.items(), ids=NEGATIVES)
def test_near_misses_do_not_match_union_find(name, code):
    direct = UnionFindDetector().detect(ast.parse(code))
    actual = run_analysis(code, accepted_solution_groups=GROUPS[:1])
    assert "error" not in actual
    assert not direct.detected, name
    assert direct.confidence == 0, name
    assert actual["match_result"]["match_result"] == "NO_MATCH", name
    assert actual["match_result"]["matched_groups"] == []
