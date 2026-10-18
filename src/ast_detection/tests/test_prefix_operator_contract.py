"""Sum evidence is additive; valid prefix products need not fit this label."""
import ast

import pytest

from src.ast_detection.detectors.prefix_sum import PrefixSumDetector
from pathforge.api.services.analysis import run_analysis


def source(operator, append=False, weighted=False):
    update = f"items[index] {'* 2' if weighted else ''}".strip()
    statement = f"totals.append(totals[-1] {operator} {update})" if append else f"totals[index + 1] = totals[index] {operator} {update}"
    return f"def solve(items):\n    totals = [0] * (len(items) + 1)\n    for index in range(len(items)):\n        {statement}\n    return totals\n"


@pytest.mark.parametrize("renamed", [False, True])
@pytest.mark.parametrize("append", [False, True])
@pytest.mark.parametrize("operator,weighted", [("+", False), ("-", False), ("+", True)])
def test_additive_prefix_forms_preserve_real_detection_and_matching(renamed, append, operator, weighted):
    code = source(operator, append, weighted)
    if renamed:
        code = code.replace('items', 'values').replace('totals', 'products').replace('index', 'position')
    assert PrefixSumDetector().detect(ast.parse(code)).detected
    result = run_analysis(code, accepted_solution_groups=[{"patterns": ["prefix_sum"]}])
    assert result["match_result"]["match_result"] == "FULL_MATCH"


@pytest.mark.parametrize("renamed", [False, True])
@pytest.mark.parametrize("append", [False, True])
def test_product_scan_is_not_promoted_to_additive_prefix_sum(renamed, append):
    code = source('*', append).replace('[0]', '[1]')
    if renamed:
        code = code.replace('items', 'values').replace('totals', 'prefix_sums').replace('index', 'position')
    assert not PrefixSumDetector().detect(ast.parse(code)).detected
    result = run_analysis(code, accepted_solution_groups=[{"patterns": ["prefix_sum"]}])
    assert 'prefix_sum' not in {p['pattern_id'] for p in result['ast']['detected_patterns']}
    assert result['match_result']['match_result'] == 'NO_MATCH'
