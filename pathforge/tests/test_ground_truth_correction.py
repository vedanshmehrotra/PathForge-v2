"""Offline candidate preparation shares real builder semantics; never activates."""
import copy
import json
from unittest.mock import Mock

import pytest

from pathforge.tests.test_shadow_display_contract import isolated_services


@pytest.fixture
def workflow(monkeypatch):
    with isolated_services():
        from pathforge.services import ground_truth_builder as builder, ground_truth_correction as correction
        forbidden = Mock(side_effect=AssertionError("Candidate preparation must not invoke an LLM"))
        monkeypatch.setattr(builder, "call_llm", forbidden)
        yield builder, correction
        forbidden.assert_not_called()


@pytest.fixture
def request_data():
    return {
        "problem": {"id": 209, "title": "Synthetic local problem", "description": "Frozen problem source"},
        "previous_ground_truth": {"problem_id": 209, "patterns": "[\"binary_search_standard\"]",
                                  "solution_groups": [{"authority_tier": "externally_listed"}],
                                  "validation_status": "externally_listed", "historical_field": "preserve exactly"},
        "proposed_response": {"patterns": ["prefix_sum", "hash_map_lookup"], "approaches": [
            {"name": "Totals with lookup", "patterns": ["prefix_sum", "hash_map_lookup"]}]},
        "correction_reason": "Synthetic mismatch for storage-boundary testing; not a production correction",
    }


def test_candidate_preserves_old_artifact_without_inheriting_authority(workflow, request_data):
    _builder, correction = workflow
    before = copy.deepcopy(request_data)
    package = correction.prepare_correction(request_data)
    assert request_data == before
    assert package["previous_artifact"] == before["previous_ground_truth"]
    assert package["previous_sha256"] == correction.artifact_sha256(before["previous_ground_truth"])
    assert package["state"] == "PREPARED_NOT_ACTIVE"
    assert package["proposed_artifact"]["validation_status"] == "llm_proposed"
    for group in package["proposed_artifact"]["solution_groups"]:
        assert group["authority_tier"] == group["evidence"] == "llm_proposed"
        assert group["approach_definition"] == "EXPLICIT"
    assert all(package["generation"][key] is None for key in ("model", "prompt_version", "generated_at"))
    assert package["generation"]["metadata_source"] == "caller_supplied_not_independently_verified"
    digest = package.pop("package_sha256")
    assert digest == correction.artifact_sha256(package)
    package["previous_artifact"]["historical_field"] = "changed copy"
    assert request_data == before


@pytest.mark.parametrize("kind", ["composite", "alternatives", "canonical_uncovered"])
def test_candidate_equals_actual_builder_sql_payload(workflow, request_data, monkeypatch, kind):
    builder, correction = workflow
    if kind == "alternatives":
        request_data["proposed_response"] = {
            "patterns": ["binary_search_standard", "two_pointers_opposite"], "approaches": [
                {"patterns": ["binary_search_standard"]}, {"patterns": ["two_pointers_opposite"]}]}
    elif kind == "canonical_uncovered":
        request_data["proposed_response"] = {
            "patterns": ["dfs_iterative"], "approaches": [{"patterns": ["dfs_iterative"]}]}
    package = correction.prepare_correction(request_data)
    llm = Mock(return_value=copy.deepcopy(request_data["proposed_response"]))
    connection = Mock(spec=["execute", "commit", "rollback"])
    with monkeypatch.context() as local:
        local.setattr(builder, "call_llm", llm)
        builder.build_ground_truth(209, request_data["problem"]["description"], connection)
    llm.assert_called_once()
    connection.execute.assert_called_once()
    params = connection.execute.call_args.args[1]
    proposed = package["proposed_artifact"]
    assert json.loads(params[1]) == proposed["patterns"]
    assert json.loads(params[2]) == proposed["confidence"]
    assert json.loads(params[3]) == proposed["solution_groups"]
    connection.commit.assert_not_called()
    if kind == "composite":
        assert len(proposed["solution_groups"]) == 1
        assert set(proposed["solution_groups"][0]["patterns"]) == {"prefix_sum", "hash_map_lookup"}
    elif kind == "alternatives":
        assert all(group["family_relation"] == "ONE_OF" for group in proposed["solution_groups"])
    else:
        assert proposed["solution_groups"][0]["matchable"] is False
        assert any("Canonical coverage" in limitation for limitation in package["limitations"])


@pytest.mark.parametrize("old_patterns", [[None], [{}], [], "invalid historical JSON"])
def test_malformed_existing_rows_can_be_preserved_without_repairing_them(workflow, request_data, old_patterns):
    _builder, correction = workflow
    request_data["previous_ground_truth"]["patterns"] = old_patterns
    assert correction.prepare_correction(request_data)["previous_artifact"]["patterns"] == old_patterns


@pytest.mark.parametrize("raw", [None, {}, {"patterns": []}, {"patterns": [None]},
    {"patterns": ["unsupported_depth"], "approaches": [{"patterns": ["unsupported_depth"]}]},
    {"patterns": ["prefix_sum"], "approaches": [{"patterns": [{}]}]}])
def test_rejected_proposals_are_controlled_generation_errors(workflow, request_data, raw):
    builder, correction = workflow
    request_data["proposed_response"] = raw
    with pytest.raises(builder.GroundTruthError):
        correction.prepare_correction(request_data)


@pytest.mark.parametrize("alteration", ["wrong_problem", "missing_reason", "no_approaches",
    "failed_generation", "unknown_metadata", "malformed_metadata"])
def test_inconsistent_correction_request_is_rejected(workflow, request_data, alteration):
    _builder, correction = workflow
    if alteration == "wrong_problem":
        request_data["previous_ground_truth"]["problem_id"] = 20
    elif alteration == "missing_reason":
        request_data["correction_reason"] = " "
    elif alteration == "no_approaches":
        request_data["proposed_response"].pop("approaches")
    elif alteration == "failed_generation":
        request_data["generation"] = {"finish_reason": "length"}
    elif alteration == "unknown_metadata":
        request_data["generation"] = {"unrecognized_setting": "not accepted"}
    else:
        request_data["generation"] = []
    with pytest.raises(correction.CorrectionPreparationError):
        correction.prepare_correction(request_data)


def test_raw_authority_claims_do_not_promote_a_candidate(workflow, request_data):
    _builder, correction = workflow
    request_data["proposed_response"]["validation_status"] = "HUMAN_APPROVED"
    request_data["proposed_response"]["approaches"][0].update(
        authority_tier="EXTERNAL_VERIFIED", evidence="externally_listed")
    group = correction.prepare_correction(request_data)["proposed_artifact"]["solution_groups"][0]
    assert group["authority_tier"] == group["evidence"] == "llm_proposed"


def test_invalid_source_shape_is_not_silently_replaced_by_a_title(workflow, request_data):
    _builder, correction = workflow
    request_data["problem"]["description"] = []
    with pytest.raises(correction.CorrectionPreparationError, match="source fields"):
        correction.prepare_correction(request_data)


def test_cli_writes_only_an_exclusive_external_package(workflow, request_data, tmp_path):
    from scripts.prepare_ground_truth_correction import main

    request_file, output = tmp_path / "request.json", tmp_path / "package.json"
    request_file.write_text(json.dumps(request_data), encoding="utf-8")
    original = request_file.read_bytes()
    args = ["--input", str(request_file), "--output", str(output)]
    assert main(args) == 0
    assert json.loads(output.read_text())["state"] == "PREPARED_NOT_ACTIVE"
    package_bytes = output.read_bytes()
    assert main(args) == 1
    assert output.read_bytes() == package_bytes
    assert request_file.read_bytes() == original
    assert main(["--input", str(request_file), "--output", str(request_file)]) == 1
    assert request_file.read_bytes() == original


def test_cli_rejection_creates_no_output(workflow, request_data, tmp_path):
    from scripts.prepare_ground_truth_correction import main

    request_data["proposed_response"]["patterns"] = []
    request_file, output = tmp_path / "bad.json", tmp_path / "absent.json"
    request_file.write_text(json.dumps(request_data), encoding="utf-8")
    assert main(["--input", str(request_file), "--output", str(output)]) == 1
    assert not output.exists()


def test_cli_rejects_repository_output_before_writing(workflow, request_data, tmp_path):
    from scripts.prepare_ground_truth_correction import ROOT, main

    source = tmp_path / "input.json"
    source.write_text(json.dumps(request_data), encoding="utf-8")
    destination = ROOT / "must-not-create-correction.json"
    with pytest.raises(SystemExit) as error:
        main(["--input", str(source), "--output", str(destination)])
    assert error.value.code == 2
    assert not destination.exists()
