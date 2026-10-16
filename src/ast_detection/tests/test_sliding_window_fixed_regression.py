"""Source-reviewed fixed-window regressions through the real production engines."""

import ast
from pathlib import Path
import socket
from textwrap import dedent

import pytest

from pathforge.api.services.analysis import run_analysis
from src.ast_detection.detectors.sliding_window_fixed import SlidingWindowFixedDetector


CASE_NAMES = (
    "sw_for_with_inner_while",
    "sw_without_hash",
    "fw_max_sum_k",
    "fw_max_sum_subarray_k_renamed",
)


def _reviewed_cases():
    # Read only the code literals, never execute the corpus or use its labels.
    corpus = Path(__file__).resolve().parents[3] / (
        "pathforge/ast_analysis/shadow/tests/evaluation_corpus.py"
    )
    cases = {}
    for node in ast.walk(ast.parse(corpus.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "add":
            name = ast.literal_eval(node.args[0])
            if name in CASE_NAMES:
                cases[name] = ast.literal_eval(node.args[1])
    assert set(cases) == set(CASE_NAMES)
    return cases


REVIEWED_CASES = _reviewed_cases()
GROUPS = [{"patterns": ["sliding_window_fixed"]}, {"patterns": ["binary_search_classic"]}]


@pytest.fixture(autouse=True)
def isolated_engines(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Detector tests must not connect to a database or external service")

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setattr("psycopg2.connect", forbidden)
    monkeypatch.setattr("psycopg2.pool.ThreadedConnectionPool", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def _assert_fixed_window(code):
    direct = SlidingWindowFixedDetector().detect(ast.parse(code))
    actual = run_analysis(code, accepted_solution_groups=GROUPS)
    assert "error" not in actual
    match = actual["match_result"]
    assert (direct.detected, match["match_result"], match["matched_groups"]) == (
        True, "FULL_MATCH", [0],
    )
    assert 0 < direct.confidence <= 1
    assert any(p["pattern_id"] == "sliding_window_fixed" for p in actual["ast"]["detected_patterns"])
    return direct


@pytest.mark.parametrize("name", CASE_NAMES)
def test_reviewed_corpus_reaches_real_matching(name):
    # Each source initializes sum(sequence[:width]) and maintains that same
    # accumulator with incoming[i] minus outgoing[i-width], at a fixed width.
    _assert_fixed_window(REVIEWED_CASES[name])


def test_equivalent_renaming_preserves_detection_and_confidence():
    tree = ast.parse(REVIEWED_CASES["fw_max_sum_k"])
    aliases = {"nums": "samples", "k": "span", "n": "length", "i": "cursor",
               "window_sum": "aggregate", "max_sum": "record"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            node.id = aliases.get(node.id, node.id)
        elif isinstance(node, ast.arg):
            node.arg = aliases.get(node.arg, node.arg)
    original = _assert_fixed_window(REVIEWED_CASES["fw_max_sum_k"])
    renamed = _assert_fixed_window(ast.unparse(tree))
    assert renamed.confidence == original.confidence


@pytest.mark.parametrize("update", [
    "total += values[index] - values[index - width]",
    "total += values[index]\n        total -= values[index - width]",
])
def test_combined_and_separate_updates(update):
    code = f"""
def windows(values, width):
    total = sum(values[:width])
    outputs = [total]
    for index in range(width, len(values), 1):
        {update}
        outputs.append(total)
    return outputs
"""
    _assert_fixed_window(code)


def test_positive_literal_width():
    _assert_fixed_window("""
def windows(values):
    total = sum(values[:3])
    for index in range(3, len(values)):
        total += values[index] - values[index - 3]
    return total
""")


NEGATIVE_UPDATES = {
    "running_total": "total += values[index]",
    "adjacent_differences": "total += values[index] - values[index - 1]",
    "unrelated_subtraction": "total += values[index] - width",
    "different_sequences": "total += values[index] - other[index - width]",
    "different_incoming_index": "total += values[index + 1] - values[index - width]",
    "different_outgoing_index": "total += values[index] - values[index + width]",
    "different_accumulators": "total += values[index]\n        other_total -= values[index - width]",
    "changed_width": "total += values[index] - values[index - width]\n        width += 1",
    "changed_index": "index += 1\n        total += values[index] - values[index - width]",
    "overwritten_accumulator": "total += values[index] - values[index - width]\n        total = 0",
    "variable_window": "total += values[index]\n        while total > limit:\n            total -= values[left]\n            left += 1",
    "changed_sequence": "total += values[index] - values[index - width]\n        values[index] = 0",
    "sequence_receiver_mutation": "total += values[index] - values[index - width]\n        values.pop()",
}


@pytest.mark.parametrize("name,update", NEGATIVE_UPDATES.items(), ids=NEGATIVE_UPDATES)
def test_near_misses_do_not_match_fixed_window(name, update):
    code = f"""
def near_miss(values, other, width, limit):
    total = sum(values[:width])
    other_total = 0
    left = 0
    for index in range(width, len(values)):
        {update}
    return total
"""
    direct = SlidingWindowFixedDetector().detect(ast.parse(code))
    actual = run_analysis(code, accepted_solution_groups=GROUPS[:1])
    assert "error" not in actual
    assert not direct.detected, name
    assert direct.confidence == 0
    assert actual["match_result"]["match_result"] == "NO_MATCH", name
    assert actual["match_result"]["matched_groups"] == []


@pytest.mark.parametrize("initial, start, step", [
    ("0", "width", "1"),
    ("sum(values[:width - 1])", "width", "1"),
    ("sum(other[:width])", "width", "1"),
    ("sum(values[:width])", "0", "1"),
    ("sum(values[:width])", "width", "2"),
])
def test_update_requires_matching_initial_window_and_unit_advance(initial, start, step):
    code = f"""
def near_miss(values, other, width):
    total = {initial}
    for index in range({start}, len(values), {step}):
        total += values[index] - values[index - width]
    return total
"""
    assert not SlidingWindowFixedDetector().detect(ast.parse(code)).detected
    assert run_analysis(code, accepted_solution_groups=GROUPS[:1])["match_result"]["matched_groups"] == []


@pytest.mark.parametrize("interlude", ["width += 1", "values.reverse()", "total = 0"])
def test_initial_window_must_still_be_valid_at_loop_entry(interlude):
    code = f"""
def near_miss(values, width):
    total = sum(values[:width])
    {interlude}
    for index in range(width, len(values)):
        total += values[index] - values[index - width]
    return total
"""
    assert not SlidingWindowFixedDetector().detect(ast.parse(code)).detected
    assert run_analysis(code, accepted_solution_groups=GROUPS[:1])["match_result"]["match_result"] == "NO_MATCH"


def test_existing_boundary_form_keeps_its_evidence_and_confidence():
    code = dedent("""
        total = 0
        left = 0
        for right in range(len(values)):
            total += values[right]
            if right >= width - 1:
                best = max(best, total)
                total -= values[left]
                left += 1
    """)
    result = _assert_fixed_window(code)
    assert result.confidence == pytest.approx(0.85)
    assert [e.type for e in result.evidence] == [
        "window_size_check", "window_expand", "window_shrink_fixed",
    ]
