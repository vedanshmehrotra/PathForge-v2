"""Offline acceptance entry point. Block database/network before backend imports.

python scripts/verify_foundation.py --output <external-directory> [--assessment-only]
Submitted sources are parsed, not executed. Output contains synthetic fixtures.
"""
import argparse
from contextlib import contextmanager, ExitStack
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@contextmanager
def offline():
    attempts = []

    def deny(*args, **kwargs):
        attempts.append('database/network')
        raise AssertionError('Configured databases and external services are forbidden')

    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ))
        os.environ.pop('DATABASE_URL', None)
        os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
        for target in ('dotenv.load_dotenv',):
            stack.enter_context(patch(target, return_value=False))
        for target in ('psycopg2.connect', 'psycopg2.pool.ThreadedConnectionPool',
                       'socket.create_connection', 'socket.getaddrinfo', 'urllib.request.urlopen'):
            stack.enter_context(patch(target, side_effect=deny))
        stack.enter_context(patch.object(socket.socket, 'connect', side_effect=deny))
        stack.enter_context(patch.object(socket.socket, 'connect_ex', side_effect=deny))
        yield
    if attempts:
        raise AssertionError(f'Forbidden external-access attempts: {len(attempts)}')


def assess(specifications):
    from types import SimpleNamespace
    from unittest.mock import Mock
    import config
    from pathforge.api.routes import analyze
    from pathforge.services import ground_truth_builder as builder, persistence, product_eligibility as b6
    from pathforge.tests.test_problem_preparation_boundary import MemoryConnection, PROBLEM
    from pathforge.ast_analysis.shadow import persistence as shadow_storage
    from src.ast_detection.semantic.shadow_detector import ShadowDetector

    class Connection(MemoryConnection):
        def execute(self, sql, params):
            if 'INSERT INTO submissions' in sql:
                self.writes.append('submission')
                return SimpleNamespace(fetchone=lambda: {'id': 123})
            return super().execute(sql, params)

    rows = []
    for spec in specifications:
        connection = Connection(problem={**PROBLEM, 'title': spec['problem']}, ground_truth=None)
        raw = {'patterns': spec['patterns'], 'approaches': [{'name': spec['problem'], 'patterns': spec['patterns']}]}
        with patch.object(builder, 'call_llm', return_value=raw):
            builder.build_ground_truth(209, 'Synthetic local preparation fixture', connection)
        forbidden = Mock(side_effect=AssertionError('Proposed expectations must not update skill models'))
        with ExitStack() as stack:
            for target, value in (
                (analyze, ('get_current_user', Mock(return_value=SimpleNamespace(user_id=7)))),
                (analyze, ('get_connection', Mock(return_value=connection))),
                (persistence, ('_next_attempt_number', Mock(return_value=1))),
                (persistence, ('_update_user_streak', Mock())),
                (persistence, ('update_topic_profile', forbidden)),
                (persistence, ('get_recommendation', forbidden)),
                (persistence, ('_gap_engine', SimpleNamespace(compute_signals=forbidden, persist_signals=forbidden))),
                (persistence, ('_elo_engine', SimpleNamespace(compute_updates=forbidden, persist_elos=forbidden))),
                (b6, ('flag_enabled', Mock(return_value=False))),
                (config, ('SHADOW_AUTHORITY_PRODUCT_GATING', False)),
                (shadow_storage, ('persist_shadow_analysis', Mock())),
                (ShadowDetector, ('analyze_safe', Mock(return_value=None))),
                (builder, ('call_llm', Mock(side_effect=AssertionError('Analysis must remain DB-only')))),
            ):
                stack.enter_context(patch.object(target, value[0], value[1]))
            response = analyze.analyze_endpoint(analyze.AnalyzeRequest(
                user_id=999, code=spec['code'], problem={'leetcode_id': 209}), None).model_dump()
            groups = json.loads(connection.ground_truth['solution_groups'])
            canonical = b6.evaluate_submission(spec['code'], groups)
        forbidden.assert_not_called()
        assert connection.writes == ['ground_truth', 'submission']
        assert response['persisted']['skill_updates_skipped'] is True
        assert response['elo_updates'] == [] and response['persisted']['gap_signals_count'] == 0
        assert canonical is not None and not canonical['eligibility'].eligible
        detections = {p['pattern_id'] for p in response['ast']['detected_patterns']}
        selected = response['shadow_analysis']['strategy_selection']['submission']['selected']
        rows.append({**spec, 'response': response,
                     'missing_expected_patterns': sorted(set(spec['expected_present']) - detections),
                     'unexpected_patterns': sorted(set(spec['expected_absent']) & detections),
                     'strategy_missed': spec['expected_strategy'] is not None and selected != spec['expected_strategy'],
                     'unsafe_strategy': selected in spec['forbidden_strategies'],
                     'canonical_eligibility': canonical['eligibility'].to_dict()})
    return rows


def practice_fixtures():
    """Actual service output for mixed daily practice, not inferred skill."""
    from itertools import combinations
    from pathforge.tests.test_practice_recommendations import practice_service, PROBLEMS
    fixtures = {}
    history = [{'problem_id': 888}, {'problem_id': 999}]
    for size in range(len(PROBLEMS) + 1):
        for excluded in combinations(sorted(str(p['id']) for p in PROBLEMS), size):
            for difficulty in (None, 'Easy', 'Medium', 'Hard'):
                with practice_service(history) as (service, _):
                    result = service.get_recommendations(7, mode='practice', difficulty=difficulty, excluded_ids=excluded)
                assert result['policy'] == 'recorded_practice_v1'
                assert result['summary']['primary_weak_patterns'] == []
                assert all(p['score'] is None and not p['pattern'] for p in result['recommendations'])
                fixtures[json.dumps([difficulty, list(excluded)], separators=(',', ':'))] = result
    return fixtures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--assessment-only', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        parser.error('Keep generated evidence outside the repository')
    output.mkdir(parents=True, exist_ok=True)
    from experiments.code_analysis_evaluation.foundation_cases import cases
    specifications = cases()
    frozen = json.dumps(specifications, sort_keys=True, indent=2)
    (output / 'expectations.json').write_text(frozen, encoding='utf-8')
    digest = hashlib.sha256(frozen.encode()).hexdigest()
    with offline():
        rows = assess(specifications)
        (output / 'assessment.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
        practice = practice_fixtures()
        (output / 'practice.json').write_text(json.dumps(practice, indent=2), encoding='utf-8')
        from pathforge.tests.test_unscored_approaches import build_contract_cases
        approach_cases = build_contract_cases()
        (output / 'approach-contract.json').write_text(json.dumps(approach_cases, indent=2), encoding='utf-8')
        summary = {'cases': len(rows), 'problem_families': len({s['problem'] for s in specifications if s['split'] != 'negative'}),
                   'expectations_sha256': digest,
                   'legacy_expected_pattern_misses': [r['id'] for r in rows if r['missing_expected_patterns']],
                   'targeted_false_positive_cases': [r['id'] for r in rows if r['unexpected_patterns']],
                   'canonical_support_gaps': [r['id'] for r in rows if r['strategy_missed']],
                   'unsafe_strategy_cases': [r['id'] for r in rows if r['unsafe_strategy']],
                   'proposed_cases_with_skill_updates': 0,
                   'practice_service_scenarios': len(practice),
                   'approach_contract_scenarios': len(approach_cases),
                   'scope': 'Synthetic expectations, actual builder/resolver/engines/persistence/API; no code execution or external services.'}
        (output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        print(json.dumps(summary, indent=2))
        if not args.assessment_only:
            import pytest
            os.chdir(ROOT)
            # Use a fresh artifact-local directory, not an inaccessible system
            # temp directory. Never reuse a prior pytest --basetemp (pytest
            # clears that target); the new "work" child does not exist yet.
            test_temp = Path(tempfile.mkdtemp(prefix='pytest-', dir=output)) / 'work'
            if output not in test_temp.resolve().parents or test_temp.exists():
                raise RuntimeError('Test temporary directory must be new and inside the evidence directory')
            result = pytest.main(['-q', '-p', 'no:cacheprovider', '--basetemp', str(test_temp),
                'pathforge/tests/test_approach_family_contract.py', 'pathforge/tests/test_analysis_feedback.py',
                'pathforge/tests/test_shadow_display_contract.py', 'pathforge/tests/test_b6_product_eligibility.py',
                'pathforge/tests/test_practice_recommendations.py', 'pathforge/tests/test_problem_preparation_boundary.py',
                'pathforge/tests/test_approach_evidence.py', 'pathforge/tests/test_skill_comparison_policy.py',
                'pathforge/tests/test_ground_truth_correction.py', 'pathforge/tests/test_ground_truth_builder.py',
                'pathforge/tests/test_unscored_approaches.py', 'pathforge/tests/test_llm_request_contract.py'])
            if result:
                return int(result)
    return 1 if summary['targeted_false_positive_cases'] or summary['unsafe_strategy_cases'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
