"""Source-reviewed window maintenance through actual detection and Shadow."""
import ast
from pathlib import Path
import socket

import pytest

from pathforge.api.services.analysis import run_analysis
from pathforge.ast_analysis.shadow.shadow_runner import run_shadow_analysis
from pathforge.services.product_eligibility import evaluate_submission
from src.ast_detection.detectors.sliding_window_fixed import SlidingWindowFixedDetector


def source(name):
    path = Path(__file__).parents[4] / "pathforge/ast_analysis/shadow/tests/evaluation_corpus.py"
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "add"
                and ast.literal_eval(node.args[0]) == name):
            return ast.literal_eval(node.args[1])
    raise AssertionError(name)


FIXED_CASES = ("sw_for_with_inner_while", "sw_without_hash", "fw_max_sum_k", "fw_max_sum_subarray_k_renamed")
SHRINK = """
def window(values, limit):
    left = 0
    total = 0
    best = 0
    for right in range(len(values)):
        total += values[right]
        while total > limit:
            total -= values[left]
            left += 1
        best = max(best, right - left + 1)
    return best
"""
BOUND = """
def fixed(values, width):
    total = 0
    left = 0
    best = 0
    for right in range(len(values)):
        total += values[right]
        if right >= width - 1:
            best = max(best, total)
            total -= values[left]
            left += 1
    return best
"""
TAX = """
def deduct_tax(nums, tax):
    total = 0
    for right in range(len(nums)):
        total += nums[right]
        if right >= 2:
            total -= tax
    return total
"""


def rename(code):
    tree = ast.parse(code)
    aliases = {"nums": "window_samples", "values": "window_samples", "s": "window_text",
               "right": "lead_index", "left": "trail_index", "total": "window_aggregate",
               "width": "window_span", "char_index": "last_positions"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            node.id = aliases.get(node.id, node.id)
        elif isinstance(node, ast.arg):
            node.arg = aliases.get(node.arg, node.arg)
    return ast.unparse(tree)


@pytest.fixture(autouse=True)
def no_services(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Window tests must not access a database or external service")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setattr("psycopg2.connect", forbidden)
    monkeypatch.setattr("psycopg2.pool.ThreadedConnectionPool", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def groups(tier="INFERRED"):
    return [{"id": "window", "patterns": ["sliding_window_fixed"], "required": ["sliding_window"], "authority_tier": tier}]


def shadow(code):
    result = run_shadow_analysis(code, groups())
    assert result is not None and result["coverage"] and result["strategy_selection"] and result["authority"]
    return result


@pytest.mark.parametrize("code", [TAX, rename(TAX)], ids=["named", "renamed"])
def test_scalar_tax_cannot_match_legacy_window(code):
    direct = SlidingWindowFixedDetector().detect(ast.parse(code))
    result = run_analysis(code, accepted_solution_groups=groups())
    assert "error" not in result
    assert not direct.detected
    assert result["match_result"]["match_result"] == "NO_MATCH"
    assert result["match_result"]["matched_groups"] == []


@pytest.mark.parametrize("code", [TAX, rename(TAX)], ids=["named", "renamed"])
def test_scalar_tax_cannot_establish_shadow_window(code):
    result = shadow(code)
    assert not any(s["strategy_id"] == "sliding_window" for s in result["strategy_evidence"])
    assert result["coverage"]["families"][0]["coverage_state"] == "UNRESOLVED"
    assert result["strategy_selection"]["submission"]["selected"] is None


@pytest.mark.parametrize("name", FIXED_CASES)
def test_repaired_fixed_windows_keep_real_matching_and_shadow(name):
    code = source(name)
    assert SlidingWindowFixedDetector().detect(ast.parse(code)).detected
    result = run_analysis(code, accepted_solution_groups=groups())
    assert "error" not in result and result["match_result"]["matched_groups"] == [0]
    assert shadow(code)["strategy_selection"]["submission"]["selected"] == "sliding_window"


@pytest.mark.parametrize("code", [BOUND, SHRINK, source("sw_longest_substring"), source("sw_longest_ones(self)"),
                                 source("sw_min_window_substring"), source("sw_longest_substring_k_distinct"),
                                 source("sw_contains_nearby_duplicate"), source("sw_permutation_in_string")])
def test_reviewed_window_forms_and_renaming_keep_conclusions(code):
    assert shadow(code)["strategy_selection"]["submission"]["selected"] == "sliding_window"
    assert shadow(rename(code))["strategy_selection"]["submission"]["selected"] == "sliding_window"


NEGATIVES = {
    "running_total": TAX.replace("            total -= tax", "            best = total"),
    "adjacent_differences": """
def differences(values):
    total = 0
    for index in range(1, len(values)):
        total += values[index] - values[index - 1]
    return total
""",
    "different_sequence": BOUND.replace("total -= values[left]", "total -= other[left]"),
    "different_state": BOUND.replace("total -= values[left]", "other -= values[left]"),
    "missing_trailing_advance": BOUND.replace("            left += 1", "            pass"),
    "unrelated_boundary": BOUND.replace("right >= width - 1", "ready"),
    "wrong_trailing_advance": BOUND.replace("left += 1", "left -= 1"),
    "removal_in_other_scope": BOUND.replace("            total -= values[left]", "            def remove():\n                total -= values[left]"),
    "separate_loops": """
def unrelated(values, width):
    total = 0
    left = 0
    for right in range(len(values)):
        total += values[right]
    for right in range(len(values)):
        if right >= width - 1:
            total -= values[left]
            left += 1
    return total
""",
    "unguarded_last_seen_jump": source("sw_longest_substring").replace("        if s[right] in char_index:\n", "        if ready:\n"),
    "reset_boundary_state": BOUND.replace("        total += values[right]", "        total = 0\n        total += values[right]"),
    "reset_variable_trailing": SHRINK.replace("        best = max", "        left = 0\n        best = max"),
    "advance_before_removal": SHRINK.replace("            total -= values[left]\n            left += 1", "            left += 1\n            total -= values[left]"),
    "reset_jump_boundary": source("sw_longest_substring").replace("        max_len = max", "        left = 0\n        max_len = max"),
    "dynamic_boundary_callback": BOUND.replace("right >= width - 1", "right >= boundary(right)"),
    "changed_input": SHRINK.replace("        best = max", "        values.reverse()\n        best = max"),
    "leading_rebound_by_nested_loop": BOUND.replace("        if right >=", "        for right in range(2):\n            pass\n        if right >="),
}


@pytest.mark.parametrize("name,code", NEGATIVES.items(), ids=NEGATIVES)
def test_disconnected_or_nonwindow_code_stays_inconclusive(name, code):
    result = shadow(code)
    assert not any(s["strategy_id"] == "sliding_window" for s in result["strategy_evidence"]), name
    assert result["strategy_selection"]["submission"]["selected"] is None


@pytest.mark.parametrize("tier", ["HUMAN_APPROVED", "EXTERNAL_VERIFIED"])
@pytest.mark.parametrize("code", [TAX, rename(TAX)])
def test_approved_authority_cannot_enable_scalar_tax(code, tier):
    result = evaluate_submission(code, groups(tier))
    assert result is not None and not result["eligibility"].eligible


def test_variable_window_does_not_become_a_legacy_fixed_window():
    assert not SlidingWindowFixedDetector().detect(ast.parse(SHRINK)).detected


def test_literal_boundary_still_requires_actual_outgoing_content():
    code = BOUND.replace("right >= width - 1", "right >= 2")
    assert SlidingWindowFixedDetector().detect(ast.parse(code)).detected
    assert shadow(code)["strategy_selection"]["submission"]["selected"] == "sliding_window"
    assert not SlidingWindowFixedDetector().detect(ast.parse(code.replace("total -= values[left]", "total -= tax"))).detected


@pytest.mark.parametrize("code", [BOUND, SHRINK, source("sw_longest_substring"), source("fw_max_sum_k")])
def test_window_links_do_not_change_general_technique_derivation(code):
    from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
    from pathforge.ast_analysis.shadow.relations import build_relations
    from pathforge.ast_analysis.shadow.techniques import detect_techniques
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    original = [f for f in facts if f.fact_type != "window_maintenance"]
    assert len(original) < len(facts)
    relations = build_relations(tree)
    assert detect_techniques(facts, relations) == detect_techniques(original, relations)


@pytest.mark.parametrize("case", ["sw_grumpy_bookstore", "fw_no_offset_different_code", "fw_different_structure"])
def test_reviewed_existing_offset_variants_remain_supported(case):
    # Same fixed index offset and state, with weighted element expressions,
    # explicit prefix initialization or a manually advanced while driver.
    assert shadow(source(case))["strategy_selection"]["submission"]["selected"] == "sliding_window"
