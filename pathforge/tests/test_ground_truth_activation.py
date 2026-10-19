"""Exercise explicit corrections without a configured database or provider."""
import copy
import json
import os
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from pathforge.tests.test_ground_truth_correction import workflow, request_data


@pytest.fixture
def activation(workflow, request_data):
    _builder, correction = workflow
    from pathforge.services import ground_truth_activation as service
    from pathforge.tests.test_problem_preparation_boundary import MemoryConnection, PROBLEM

    class Connection(MemoryConnection):
        def __init__(self):
            super().__init__(problem={**PROBLEM, **request_data["problem"]},
                             ground_truth=request_data["previous_ground_truth"])
            self.sql = []
            self.original = copy.deepcopy(self.ground_truth)
            self.rollback.side_effect = lambda: setattr(self, "ground_truth", copy.deepcopy(self.original))

        def execute(self, sql, params=None):
            self.sql.append(sql)
            if sql.startswith("SET LOCAL"):
                return SimpleNamespace(fetchone=lambda: None)
            if sql.startswith("UPDATE problem_ground_truth"):
                assert params[-1] == self.ground_truth["problem_id"]
                self.writes.append("ground_truth")
                self.ground_truth.update(patterns=params[0], confidence=params[1], solution_groups=json.loads(params[2]),
                                         validation_status=params[3], updated_at=params[4])
                return SimpleNamespace(fetchone=lambda: {"problem_id": params[-1]})
            return super().execute(sql, params)

    return service, correction.prepare_correction(request_data), Connection()


def test_preview_is_read_only_and_does_not_lock_or_activate(activation):
    service, package, connection = activation
    result = service.stage_correction(connection, package)
    assert not result["applied"] and result["version"] == 2
    assert connection.ground_truth == package["previous_artifact"]
    assert not connection.writes
    assert not any("FOR UPDATE" in sql or "FOR SHARE" in sql for sql in connection.sql)
    connection.commit.assert_not_called()


def test_actual_update_archives_exact_old_data_and_never_inherits_authority(activation):
    service, package, connection = activation
    original = copy.deepcopy(package)
    result = service.stage_correction(connection, package, apply=True)
    assert package == original
    assert result["applied"] and connection.writes == ["ground_truth"]
    groups = connection.ground_truth["solution_groups"]
    revision = groups[0]["correction_revision"]
    assert revision["previous_artifact"] == package["previous_artifact"]
    assert revision["previous_sha256"] == package["previous_sha256"]
    assert revision["package_sha256"] == package["package_sha256"]
    assert groups[0]["version"] == revision["version"] == 2
    assert "explicit_ground_truth_correction" in groups[0]["provenance"]
    assert connection.ground_truth["validation_status"] == "llm_proposed"
    assert groups[0]["authority_tier"] == groups[0]["evidence"] == "llm_proposed"
    assert any("FOR UPDATE" in sql for sql in connection.sql)
    assert any("FOR SHARE" in sql for sql in connection.sql)
    connection.commit.assert_not_called()  # The batch caller owns commit/rollback.


@pytest.mark.parametrize("change", ["old_row", "source", "package", "proposed_artifact", "rerun"])
def test_stale_or_edited_inputs_cannot_write(activation, change):
    service, package, connection = activation
    if change == "old_row":
        connection.ground_truth["historical_field"] = "changed after snapshot"
    elif change == "source":
        connection.problem["description"] = "changed source"
    elif change == "package":
        package["correction_reason"] = "edited after preparation"
    elif change == "proposed_artifact":
        from pathforge.services.ground_truth_correction import artifact_sha256
        package["proposed_artifact"]["solution_groups"][0]["authority_tier"] = "HUMAN_APPROVED"
        package["package_sha256"] = artifact_sha256({k: v for k, v in package.items() if k != "package_sha256"})
    else:
        service.stage_correction(connection, package, apply=True)
        connection.writes.clear()
    before = copy.deepcopy(connection.ground_truth)
    with pytest.raises(service.CorrectionActivationError):
        service.stage_correction(connection, package, apply=True)
    assert connection.writes == [] and connection.ground_truth == before


def test_explicit_revision_survives_real_cached_resolver_and_matching(activation, request_data):
    service, _package, connection = activation
    from pathforge.services.ground_truth_correction import prepare_correction
    from pathforge.services.problem_resolver import resolve_problem
    from pathforge.api.services.analysis import run_analysis
    from pathforge.api.services.approaches import describe_approaches
    from pathforge.services.approach_policy import skill_comparison_gate
    request_data["proposed_response"] = {"patterns": ["sorting", "array_traversal"],
        "approaches": [{"name": "Sort and scan", "patterns": ["sorting", "array_traversal"]}]}
    service.stage_correction(connection, prepare_correction(request_data), apply=True)
    before = copy.deepcopy(connection.ground_truth)
    context = resolve_problem(connection, leetcode_id=209, allow_preparation=False)
    source = 'def positions(nums, target):\n    nums.sort()\n    result=[]\n    for i, x in enumerate(nums):\n        if x==target:\n            result.append(i)\n    return result'
    result = run_analysis(source, accepted_solution_groups=context.accepted_solution_groups)
    assert result["match_result"]["match_result"] == "FULL_MATCH"
    assert describe_approaches(context.accepted_solution_groups, result["ast"])[0].pattern_evidence_state == "ALL_OBSERVED"
    assert not skill_comparison_gate(context.accepted_solution_groups, result["ast"], result["match_result"])["eligible"]
    assert context.accepted_solution_groups[0]["version"] == 2
    assert connection.ground_truth == before and connection.writes == ["ground_truth"]


def test_next_revision_retains_the_complete_previous_revision(activation, request_data):
    service, package, connection = activation
    from pathforge.services.ground_truth_correction import prepare_correction
    service.stage_correction(connection, package, apply=True)
    request_data["previous_ground_truth"] = copy.deepcopy(connection.ground_truth)
    next_package = prepare_correction(request_data)
    service.stage_correction(connection, next_package, apply=True)
    revision = connection.ground_truth["solution_groups"][0]["correction_revision"]
    assert revision["version"] == 3
    assert revision["previous_artifact"] == next_package["previous_artifact"]
    assert revision["previous_artifact"]["solution_groups"][0]["correction_revision"]["previous_artifact"] == package["previous_artifact"]


def test_second_target_failure_rolls_back_the_whole_cli_batch(activation, request_data, tmp_path):
    _service, package, connection = activation
    from pathforge.services.ground_truth_correction import prepare_correction
    from scripts.activate_ground_truth_correction import main
    request_data["problem"]["id"] = request_data["previous_ground_truth"]["problem_id"] = 210
    other = prepare_correction(request_data)
    paths = [tmp_path / "first.json", tmp_path / "second.json"]
    for file, value in zip(paths, [package, other]):
        file.write_text(json.dumps(value), encoding="utf-8")
    raw = Mock()
    raw.rollback.side_effect = connection.rollback
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://fixture.invalid/test"}), \
         patch("psycopg2.connect", return_value=raw), patch("pathforge.db.db.PgConnection", return_value=connection):
        assert main(["--package", str(paths[0]), "--package", str(paths[1]), "--apply"]) == 1
    assert connection.writes == ["ground_truth"]  # The first UPDATE was staged.
    assert connection.ground_truth == connection.original  # Then rolled back.
    raw.commit.assert_not_called()
    raw.rollback.assert_called_once()


def test_correction_digest_is_stable_across_python_hash_seeds(workflow, request_data):
    request_data["proposed_response"] = {"patterns": ["sorting", "array_traversal", "brute_force"],
        "approaches": [{"patterns": ["sorting", "array_traversal", "brute_force"]}]}
    program = ('from scripts.verify_foundation import offline\n'
               'with offline():\n'
               ' from pathforge.services.ground_truth_correction import prepare_correction\n'
               ' import json,sys\n'
               ' print(prepare_correction(json.loads(sys.argv[1]))["proposed_sha256"])')
    digests = [subprocess.check_output([sys.executable, '-B', '-c', program, json.dumps(request_data)],
               env={**os.environ, 'PYTHONHASHSEED': seed}, text=True).strip() for seed in ('1', '2', '4')]
    assert len(set(digests)) == 1


@pytest.mark.parametrize("apply,fail", [(False, False), (True, False), (True, True)])
def test_cli_commits_only_a_complete_explicit_batch(activation, tmp_path, capsys, apply, fail):
    _service, package, connection = activation
    from scripts.activate_ground_truth_correction import main
    file = tmp_path / "package.json"
    file.write_text(json.dumps(package), encoding="utf-8")
    raw = Mock()
    if fail:
        raw.commit.side_effect = RuntimeError("simulated database failure")
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://fixture.invalid/test"}), \
         patch("psycopg2.connect", return_value=raw), patch("pathforge.db.db.PgConnection", return_value=connection):
        code = main(["--package", str(file)] + (["--apply"] if apply else []))
    assert code == (1 if fail else 0)
    assert raw.set_session.call_args.kwargs == {"readonly": not apply, "autocommit": False}
    assert raw.commit.call_count == int(apply)
    assert raw.rollback.call_count == int(not apply or fail)
    raw.close.assert_called_once()
    assert ("COMMITTED" in capsys.readouterr().out) == (apply and not fail)
