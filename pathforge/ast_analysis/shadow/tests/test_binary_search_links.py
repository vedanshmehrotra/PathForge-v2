"""Source-reviewed S1 partition and feasibility boundaries, through real engines."""
import ast
from pathlib import Path
import socket

import pytest

from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
from pathforge.services.product_eligibility import evaluate_submission


def corpus_source(name):
    path = Path(__file__).parents[4] / "pathforge/ast_analysis/shadow/tests/evaluation_corpus.py"
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "add" and ast.literal_eval(node.args[0]) == name):
            return ast.literal_eval(node.args[1])
    raise AssertionError(name)


ANSWER = corpus_source("bs_answer_space")
CLASSIC = corpus_source("bs_standard")
CALLER = ANSWER[:ANSWER.index("def can_finish")]


@pytest.fixture(autouse=True)
def no_services(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("S1 tests must not access a database or external service")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setattr("psycopg2.connect", forbidden)
    monkeypatch.setattr("psycopg2.pool.ThreadedConnectionPool", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def groups(tier="INFERRED"):
    return [{"id": "search", "patterns": ["binary_search_standard"],
             "required": ["binary_search"], "authority_tier": tier}]


def checked(code):
    result = run_shadow_analysis(code, groups())
    assert result is not None, "Graceful failure is not an acceptable negative result"
    assert result["coverage"] and result["strategy_selection"] and result["authority"]
    return result


def assert_inconclusive(code):
    result = checked(code)
    assert "binary_search" not in [s["strategy_id"] for s in result["strategy_evidence"]]
    assert result["coverage"]["families"][0]["coverage_state"] != "CONFIRMED"
    assert result["strategy_selection"]["submission"]["selected"] is None
    return result


@pytest.mark.parametrize("name", [
    "bs_standard", "bs_renamed_vars", "bs_rshift", "bs_overflow_safe",
    "bs_class_method", "bs_nested_if", "bs_leftmost", "bs_three_conditions",
    "bs_alternate_condition", "bs_min_in_rotated", "bs_peak_element", "bs_rotated",
    "bs_answer_space",
])
def test_reviewed_searches_keep_canonical_conclusions(name):
    # These bodies make a midpoint-based partition decision and update its
    # bounds. The ceiling-sum helper is the explicitly authorized family.
    result = checked(corpus_source(name))
    assert result["coverage"]["families"][0]["coverage_state"] == "CONFIRMED"
    assert result["strategy_selection"]["submission"]["selected"] == "binary_search"
    evidence = next(s for s in result["strategy_evidence"] if s["strategy_id"] == "binary_search")
    assert evidence["confidence"] == 0.85


def rename(code):
    tree = ast.parse(code)
    aliases = {"lo": "begin", "hi": "finish", "mid": "probe", "can_finish": "budget_ok",
               "piles": "values", "speed": "candidate", "h": "budget", "p": "item"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            node.id = aliases.get(node.id, node.id)
        elif isinstance(node, ast.arg):
            node.arg = aliases.get(node.arg, node.arg)
        elif isinstance(node, ast.FunctionDef):
            node.name = aliases.get(node.name, node.name)
    return ast.unparse(tree)


@pytest.mark.parametrize("code", [CLASSIC, ANSWER])
def test_renaming_preserves_search_conclusion(code):
    assert checked(rename(code))["strategy_selection"]["submission"]["selected"] == "binary_search"


def test_existing_true_division_signature_remains_structural_evidence():
    # Existing Shadow support recognizes the linked search structure. Python
    # float indexing can still fail at runtime; this is not a correctness test.
    assert checked(corpus_source("bs_true_div"))["strategy_selection"]["submission"]["selected"] == "binary_search"


def ready_loop(renamed=False):
    left, right, mid = ("begin", "finish", "probe") if renamed else ("left", "right", "mid")
    return f"""
def arbitrary_half(nums, ready):
    {left}, {right} = 0, len(nums) - 1
    while {left} <= {right}:
        {mid} = ({left} + {right}) // 2
        if ready:
            {left} = {mid} + 1
        else:
            {right} = {mid} - 1
    return {left}
"""


NEGATIVES = {
    "arbitrary_ready_named": ready_loop(),
    "arbitrary_ready_renamed": ready_loop(True),
    "constant_helper": CALLER + "def can_finish(piles, speed, h):\n    return True\n",
    "parity_helper": CALLER + "def can_finish(piles, speed, h):\n    return speed % 2 == 0\n",
    "undefined_helper": CALLER,
    "helper_ignores_candidate": ANSWER.replace("// speed", "// h"),
    "helper_rebound": ANSWER + "\ncan_finish = lambda *args: True\n",
    "helper_shadowed_by_parameter": ANSWER.replace("def min_eating_speed(piles, h):", "def min_eating_speed(piles, h, can_finish):"),
    "duplicate_helper": ANSWER + "\ndef can_finish(piles, speed, h):\n    return True\n",
    "builtin_sum_rebound": ANSWER + "\nsum = lambda values: 0\n",
    "wrong_candidate_argument": ANSWER.replace("can_finish(piles, mid, h)", "can_finish(piles, h, mid)"),
    "midpoint_overwritten": CLASSIC.replace("        if nums[mid]", "        mid = target\n        if nums[mid]", 1),
    "midpoint_elsewhere": ready_loop().replace("        mid = (left + right) // 2\n", "") + "\ndef unrelated(left, right):\n    return (left + right) // 2\n",
    "comparison_elsewhere": ready_loop() + "\ndef unrelated(nums, mid, target):\n    if nums[mid] < target:\n        return True\n",
    "disconnected_updates": CLASSIC.replace("        elif nums[mid] < target:", "        elif ready:"),
    "linear_updates": CLASSIC.replace("lo = mid + 1", "lo = lo + 1").replace("hi = mid - 1", "hi = hi - 1"),
    "helper_wrong_scope": CALLER + "class Other:\n    " + "\n    ".join(ANSWER[ANSWER.index("def can_finish"):].strip().splitlines()) + "\n",
    "ready_or_comparison": CLASSIC.replace("elif nums[mid] < target:", "elif ready or nums[mid] < target:"),
    "wrong_partition_direction": ANSWER.replace("hi = mid", "hi = mid + 1"),
    "midpoint_overwritten_in_condition": CLASSIC.replace("        if nums[mid]", "        if (mid := target):\n            pass\n        if nums[mid]", 1),
    "changed_budget_in_loop": ANSWER.replace("        if can_finish", "        h = h + 1\n        if can_finish"),
    "different_feasibility_inputs": CALLER.replace(
        "        if can_finish(piles, mid, h):\n            hi = mid\n        else:\n            lo = mid + 1",
        "        if can_finish(piles, mid, h):\n            hi = mid\n        if not can_finish(other, mid, h):\n            lo = mid + 1",
    ) + ANSWER[ANSWER.index("def can_finish"):],
    "ordered_comparison_does_not_control_updates": CLASSIC.replace(
        "        if nums[mid] == target:\n            return mid\n        elif nums[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid - 1",
        "        if nums[mid] == target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n        if nums[mid] < target:\n            print(mid)",
    ),
}


@pytest.mark.parametrize("name,code", NEGATIVES.items(), ids=NEGATIVES)
def test_unlinked_or_unsupported_predicates_are_inconclusive(name, code):
    result = assert_inconclusive(code)
    if name in {"arbitrary_ready_named", "arbitrary_ready_renamed", "constant_helper", "parity_helper", "undefined_helper"}:
        assert result["coverage"]["families"][0]["coverage_state"] == "UNRESOLVED"


@pytest.mark.parametrize("tier", ["HUMAN_APPROVED", "EXTERNAL_VERIFIED"])
@pytest.mark.parametrize("name,code", NEGATIVES.items(), ids=NEGATIVES)
def test_approved_authority_cannot_enable_unsupported_search(name, code, tier):
    result = evaluate_submission(code, groups(tier))
    assert result is not None
    assert result["eligibility"].eligible is False


@pytest.mark.parametrize("tier,eligible", [("HUMAN_APPROVED", True), ("EXTERNAL_VERIFIED", True),
                                          ("INFERRED", False), ("STRUCTURALLY_OBSERVED", False)])
def test_authority_policy_stays_separate_for_valid_answer(tier, eligible):
    result = evaluate_submission(ANSWER, groups(tier))
    assert result is not None
    assert result["eligibility"].eligible is eligible


def test_keyword_arguments_preserve_the_actual_candidate_link():
    code = ANSWER.replace("can_finish(piles, mid, h)", "can_finish(h=h, speed=mid, piles=piles)")
    assert checked(code)["strategy_selection"]["submission"]["selected"] == "binary_search"


def test_nested_helper_defined_before_the_loop_resolves_locally():
    caller, helper = ANSWER.split("def can_finish")
    helper = "def can_finish" + helper
    code = caller.replace("    lo, hi =", "    " + "\n    ".join(helper.strip().splitlines()) + "\n    lo, hi =", 1)
    assert checked(code)["strategy_selection"]["submission"]["selected"] == "binary_search"


def test_negated_feasibility_condition_keeps_corresponding_branches():
    code = ANSWER.replace("if can_finish(piles, mid, h):\n            hi = mid\n        else:\n            lo = mid + 1",
                          "if not can_finish(piles, mid, h):\n            lo = mid + 1\n        else:\n            hi = mid")
    assert checked(code)["strategy_selection"]["submission"]["selected"] == "binary_search"


def test_partition_evidence_has_source_provenance_and_helper_assumptions():
    result = checked(ANSWER)
    partitions = [f for f in result["structural_facts"] if f["fact_type"] == "binary_search_partition"]
    assert len(partitions) == 1
    fact = partitions[0]
    attrs = fact["attributes"]["partition"]
    assert (attrs["lower"], attrs["upper"], attrs["midpoint"], attrs["candidate_parameter"]) == ("lo", "hi", "mid", "speed")
    assert fact["ast_ref"] and attrs["helper_ref"] and attrs["midpoint_ref"] and attrs["predicate_refs"]
    assert set(attrs["update_refs"]) == {"lo", "hi"}
    assert attrs["domain_assumptions"]
    evidence = next(s for s in result["strategy_evidence"] if s["strategy_id"] == "binary_search")
    assert evidence["supporting_fact_ids"] == [fact["fact_id"]]


@pytest.mark.parametrize("code", [CLASSIC, ANSWER])
def test_partition_does_not_change_existing_technique_derivation(code):
    from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
    from pathforge.ast_analysis.shadow.relations import build_relations
    from pathforge.ast_analysis.shadow.techniques import detect_techniques
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    raw = [f for f in facts if f.fact_type != "binary_search_partition"]
    assert len(raw) < len(facts)
    relations = build_relations(tree)
    assert detect_techniques(facts, relations) == detect_techniques(raw, relations)


def test_older_raw_facts_cannot_reestablish_strategy_without_a_partition():
    from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
    from pathforge.ast_analysis.shadow.techniques import detect_techniques
    from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
    raw = [f for f in extract_structural_facts(ast.parse(CLASSIC)) if f.fact_type != "binary_search_partition"]
    assert "binary_search" not in [s.strategy_id for s in evaluate_strategies(detect_techniques(raw), raw)]
