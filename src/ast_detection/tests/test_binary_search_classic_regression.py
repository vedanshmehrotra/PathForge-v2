"""Source-reviewed binary-search regressions through the actual analysis pipeline."""

import ast
from pathlib import Path
import socket

import pytest

from pathforge.api.services.analysis import run_analysis
from src.ast_detection.detectors.binary_search_classic import BinarySearchClassicDetector


CASE_NAMES = ("bs_renamed_vars", "bs_rshift")
GROUPS = [{"patterns": ["binary_search_standard"]}, {"patterns": ["sliding_window_fixed"]}]


def _reviewed_cases():
    corpus = Path(__file__).resolve().parents[3] / (
        "pathforge/ast_analysis/shadow/tests/evaluation_corpus.py"
    )
    cases = {}
    # Extract source literals without running the corpus or trusting its labels.
    for node in ast.walk(ast.parse(corpus.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "add":
            name = ast.literal_eval(node.args[0])
            if name in CASE_NAMES:
                cases[name] = ast.literal_eval(node.args[1])
    assert set(cases) == set(CASE_NAMES)
    return cases


REVIEWED_CASES = _reviewed_cases()


@pytest.fixture(autouse=True)
def isolated_engines(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Binary-search tests must not connect to databases or external services")

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setattr("psycopg2.connect", forbidden)
    monkeypatch.setattr("psycopg2.pool.ThreadedConnectionPool", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def _assert_search(code):
    direct = BinarySearchClassicDetector().detect(ast.parse(code))
    actual = run_analysis(code, accepted_solution_groups=GROUPS)
    assert "error" not in actual
    match = actual["match_result"]
    assert (direct.detected, match["match_result"], match["matched_groups"]) == (
        True, "FULL_MATCH", [0],
    )
    assert direct.pattern_id == "binary_search_standard"
    assert direct.confidence == 1.0
    assert [item.type for item in direct.evidence] == [
        "binary_midpoint", "boundary_update", "mid_comparison", "left_right_boundary",
    ]
    assert any(p["pattern_id"] == "binary_search_standard" for p in actual["ast"]["detected_patterns"])
    return direct


@pytest.mark.parametrize("name", CASE_NAMES)
def test_reviewed_corpus_reaches_real_matching(name):
    # Both sources compare a sequence at the midpoint of their current interval
    # and narrow the corresponding bounds. Names and midpoint syntax differ.
    _assert_search(REVIEWED_CASES[name])


@pytest.mark.parametrize("name", CASE_NAMES)
def test_equivalent_renaming_preserves_detection_and_confidence(name):
    tree = ast.parse(REVIEWED_CASES[name])
    aliases = {"start": "begin", "end": "finish", "midpoint": "probe", "lo": "begin",
               "hi": "finish", "mid": "probe", "arr": "items", "nums": "items",
               "val": "needle", "target": "needle"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            node.id = aliases.get(node.id, node.id)
        elif isinstance(node, ast.arg):
            node.arg = aliases.get(node.arg, node.arg)
    original = _assert_search(REVIEWED_CASES[name])
    renamed = _assert_search(ast.unparse(tree))
    assert renamed.confidence == original.confidence


def _search_code(midpoint="(begin + finish) // 2", condition="begin <= finish",
                 comparison="items[probe] < needle", lower="probe + 1", upper="probe - 1"):
    return f"""
def search(items, needle):
    begin, finish = 0, len(items) - 1
    while {condition}:
        probe = {midpoint}
        if {comparison}:
            begin = {lower}
        else:
            finish = {upper}
    return -1
"""


@pytest.mark.parametrize("midpoint,condition,upper", [
    ("(begin + finish) // 2", "begin <= finish", "probe - 1"),
    ("(finish + begin) // 2", "finish >= begin", "probe - 1"),
    ("begin + (finish - begin) // 2", "begin <= finish", "probe - 1"),
    ("(begin + finish) >> 1", "begin <= finish", "probe - 1"),
    ("(finish + begin) >> 1", "finish >= begin", "probe - 1"),
    ("(begin + finish) // 2", "begin < finish", "probe"),
])
def test_linked_midpoint_and_interval_variants(midpoint, condition, upper):
    _assert_search(_search_code(midpoint=midpoint, condition=condition, upper=upper))


NEGATIVES = {
    "unrelated_shift": _search_code(midpoint="needle >> 1"),
    "wrong_shift": _search_code(midpoint="(begin + finish) >> 2"),
    "wrong_divisor": _search_code(midpoint="(begin + finish) // 3"),
    "unlinked_midpoint_bound": _search_code(midpoint="(begin + needle) >> 1"),
    "float_midpoint": _search_code(midpoint="(begin + finish) / 2"),
    "linear_updates": _search_code(lower="begin + 1", upper="finish - 1"),
    "wrong_lower_direction": _search_code(lower="probe - 1"),
    "wrong_upper_direction": _search_code(upper="probe + 1"),
    "different_update_midpoint": _search_code(lower="other + 1", upper="other - 1"),
    "unrelated_if": _search_code(comparison="ready"),
    "unevaluated_lambda_comparison": _search_code(comparison="(lambda: items[probe] < needle)"),
    "unrelated_ordered_comparison_in_chain": _search_code(comparison="items[probe] == needle < limit"),
    "wrong_index": _search_code(comparison="items[begin] < needle"),
    "midpoint_only_comparison": _search_code(comparison="probe < needle"),
    "feasibility_call": _search_code(comparison="feasible(probe)"),
    "negated_feasibility_call": _search_code(comparison="not feasible(probe)"),
    "mixed_feasibility_call": _search_code(comparison="items[probe] < needle and feasible(probe)"),
    "keyword_feasibility_call": _search_code(comparison="items[probe] < needle and feasible(candidate=probe)"),
    "midpoint_without_narrowing": """
def search(items, needle):
    begin, finish = 0, len(items) - 1
    while begin <= finish:
        probe = (begin + finish) >> 1
        if items[probe] == needle:
            return probe
        break
""",
    "blind_narrowing": """
def search(items, needle):
    begin, finish = 0, len(items) - 1
    while begin <= finish:
        probe = (begin + finish) >> 1
        begin = probe + 1
        finish = probe - 1
""",
    "disconnected_comparison_and_updates": """
def search(items, needle):
    begin, finish = 0, len(items) - 1
    while begin <= finish:
        probe = (begin + finish) >> 1
        if items[probe] < needle:
            print(probe)
        if ready:
            begin = probe + 1
        else:
            finish = probe - 1
""",
    "midpoint_overwritten": _search_code().replace(
        "        if items", "        probe = 0\n        if items"
    ),
    "comparison_in_other_scope": """
def search(items, needle):
    begin, finish = 0, len(items) - 1
    while begin <= finish:
        probe = (begin + finish) >> 1
        def helper():
            if items[probe] < needle:
                return probe
        begin = probe + 1
        finish = probe - 1
""",
    "linear_scan_with_misleading_names": """
def search(items, needle):
    left, right = 0, len(items) - 1
    while left <= right:
        mid = items[left] >> 1
        if items[left] == needle:
            return left
        left += 1
    return -1
""",
}


@pytest.mark.parametrize("name,code", NEGATIVES.items(), ids=NEGATIVES)
def test_near_misses_do_not_match_classic_search(name, code):
    direct = BinarySearchClassicDetector().detect(ast.parse(code))
    actual = run_analysis(code, accepted_solution_groups=GROUPS[:1])
    assert "error" not in actual
    assert not direct.detected, name
    assert direct.confidence == 0
    assert actual["match_result"]["match_result"] == "NO_MATCH", name
    assert actual["match_result"]["matched_groups"] == []


@pytest.mark.parametrize("name,code", NEGATIVES.items(), ids=NEGATIVES)
def test_conventional_names_cannot_bypass_structural_validation(name, code):
    tree = ast.parse(code)
    aliases = {"begin": "left", "finish": "right", "probe": "mid"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            node.id = aliases.get(node.id, node.id)
        elif isinstance(node, ast.arg):
            node.arg = aliases.get(node.arg, node.arg)
    test_near_misses_do_not_match_classic_search(name, ast.unparse(tree))


@pytest.mark.parametrize("renamed", [False, True], ids=["named", "renamed"])
@pytest.mark.parametrize("kind", ["linear", "unrelated_if"])
def test_cumulative_binary_search_negative_probes(kind, renamed):
    # Linear +/-1 traversal does not narrow from the midpoint. An arbitrary
    # ready flag does not make an ordered decision about the midpoint value.
    lower, upper, midpoint = ("begin", "finish", "probe") if renamed else ("left", "right", "mid")
    condition = f"nums[{midpoint}] < target" if kind == "linear" else "ready"
    lower_update = f"{lower} + 1" if kind == "linear" else f"{midpoint} + 1"
    upper_update = f"{upper} - 1" if kind == "linear" else f"{midpoint} - 1"
    code = f"""
def narrow(nums, target, ready):
    {lower}, {upper} = 0, len(nums) - 1
    while {lower} <= {upper}:
        {midpoint} = ({lower} + {upper}) // 2
        if {condition}:
            {lower} = {lower_update}
        else:
            {upper} = {upper_update}
    return {lower}
"""
    test_near_misses_do_not_match_classic_search(kind, code)


@pytest.mark.parametrize("midpoint", ["(low + high) // 2", "(low + high) >> 1"])
def test_existing_answer_space_form_is_not_promoted(midpoint):
    code = f"""
def first_feasible(max_value):
    low, high = 1, max_value
    while low < high:
        mid = {midpoint}
        if feasible(mid):
            high = mid
        else:
            low = mid + 1
    return low
"""
    assert not BinarySearchClassicDetector().detect(ast.parse(code)).detected
    actual = run_analysis(code, accepted_solution_groups=GROUPS[:1])
    assert "error" not in actual
    assert actual["match_result"]["match_result"] == "NO_MATCH"


def _predicate_probe(comparison="items[probe] < needle", nested=False):
    code = _search_code(comparison=comparison).replace(
        "def search(items, needle):", "def search(items, needle, ready, other):",
    )
    if nested:
        code = code.replace(
            "            begin = probe + 1",
            "            if ready:\n                begin = probe + 1\n            else:\n                finish = probe - 1",
        )
    return code


PREDICATE_NEGATIVES = {
    "ready_or_comparison": _predicate_probe("ready or items[probe] < needle"),
    "comparison_or_ready": _predicate_probe("items[probe] < needle or ready"),
    "ready_and_comparison": _predicate_probe("ready and items[probe] < needle"),
    "unrelated_comparison_clause": _predicate_probe("ready == 1 or items[probe] < needle"),
    "negated_unrelated_clause": _predicate_probe("not (ready or items[probe] >= needle)"),
    "different_sequences": _predicate_probe("other[probe] < needle or items[probe] < needle"),
    "borrowed_nested_guard": _predicate_probe(nested=True),
}


@pytest.mark.parametrize("name,code", PREDICATE_NEGATIVES.items(), ids=PREDICATE_NEGATIVES)
def test_predicate_clauses_cannot_borrow_partition_evidence(name, code):
    test_near_misses_do_not_match_classic_search(name, code)
    test_conventional_names_cannot_bypass_structural_validation(name, code)


@pytest.mark.parametrize("comparison", [
    "items[probe] < needle or items[probe] == needle",
    "items[probe] < needle and items[probe] <= needle",
    "not (items[probe] >= needle)",
])
def test_linked_compound_predicates_remain_supported(comparison):
    _assert_search(_search_code(comparison=comparison))


@pytest.mark.parametrize("name", ["bs_standard", "bs_nested_if", "bs_rotated", "bs_three_conditions"])
def test_reviewed_nested_partition_positives_remain_supported(name):
    corpus = Path(__file__).resolve().parents[3] / "pathforge/ast_analysis/shadow/tests/evaluation_corpus.py"
    for node in ast.walk(ast.parse(corpus.read_text(encoding="utf-8"))):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "add"
                and ast.literal_eval(node.args[0]) == name):
            code = ast.literal_eval(node.args[1])
            _assert_search(code)
            if name == "bs_rotated":
                _assert_search(code.replace("nums[lo] <= target < nums[mid]", "nums[lo] <= target and target < nums[mid]"))
            return
    raise AssertionError(name)
