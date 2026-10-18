"""Pattern overlap is observational; proposal alignment never grants authority."""
import copy

import pytest

from pathforge.tests.test_shadow_display_contract import isolated_services
from pathforge.tests.test_approach_family_contract import build_engine_cases


@pytest.fixture(scope='module')
def cases():
    return build_engine_cases()


@pytest.mark.parametrize('name,state', [
    ('tentative', 'ALL_OBSERVED'), ('fixed_alternative', 'ALL_OBSERVED'),
    ('composite_partial', 'SOME_OBSERVED'), ('nesting_depth', 'NONE_OBSERVED'),
    ('legacy_ambiguous', 'UNAVAILABLE'), ('malformed_relation', 'UNAVAILABLE'),
    ('incomplete_relation', 'UNAVAILABLE'),
])
def test_actual_api_exposes_overlap_separately_from_authority(cases, name, state):
    description = cases[name]['response']['problem_info']['solution_groups'][0]
    assert description['pattern_evidence_state'] == state
    if name == 'tentative':
        assert description['review_state'] == 'UNREVIEWED'
        assert description['authority_tier'] == 'llm_proposed'


def test_preparation_does_not_claim_unexecuted_comparison():
    with isolated_services():
        from pathforge.api.services.approaches import describe_approaches
        group = {'id': 'g', 'approach_definition': 'EXPLICIT', 'patterns': ['sliding_window_fixed'],
                 'authority_tier': 'llm_proposed', 'evidence': 'llm_proposed'}
        assert describe_approaches([group])[0].pattern_evidence_state == 'NOT_EVALUATED'


@pytest.mark.parametrize('extra', [
    {'matchable': False}, {'matchable': None}, {'matchable': 'true'},
    {'unmapped_patterns': ['sliding_window_fixed']},
    {'derivation_patterns': ['prefix_sum']},
    {'authority_tier': 'HUMAN_APPROVED', 'evidence': 'llm_proposed'},
])
def test_unusable_or_conflicting_metadata_cannot_claim_usable_approach_overlap(cases, extra):
    with isolated_services():
        from pathforge.api.services.approaches import describe_approaches
        group = {'id': 'g', 'patterns': ['sliding_window_fixed'], 'approach_definition': 'EXPLICIT',
                 'authority_tier': 'llm_proposed', 'evidence': 'llm_proposed', **extra}
        before = copy.deepcopy(group)
        result = describe_approaches([group], cases['tentative']['response']['ast'])[0]
        assert result.pattern_evidence_state == 'UNAVAILABLE'
        assert group == before


def test_display_metadata_does_not_change_canonical_decisions_or_product_eligibility(cases):
    with isolated_services():
        from pathforge.services.product_eligibility import evaluate_submission
        from pathforge.api.services.approaches import describe_approaches
        group = {'id': 'g', 'patterns': ['sliding_window_fixed'], 'required': ['sliding_window'],
                 'optional': [], 'excluded': [], 'approach_definition': 'EXPLICIT',
                 'authority_tier': 'llm_proposed', 'evidence': 'llm_proposed'}
        code = cases['tentative']['code']
        before = evaluate_submission(code, [group])
        describe_approaches([group], cases['tentative']['response']['ast'])
        after = evaluate_submission(code, [group])
        assert before['eligibility'].to_dict() == after['eligibility'].to_dict()
        assert not after['eligibility'].eligible
        for key in ('coverage', 'strategy_selection', 'authority'):
            assert before['shadow_result'][key] == after['shadow_result'][key]
