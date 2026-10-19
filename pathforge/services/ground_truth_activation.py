"""Explicit maintenance of hash-bound corrections; never called by preparation.

Revision history lives on the first ordinary solution group's JSON metadata,
so the existing schema and strict descriptive-record shape stay unchanged.
The caller owns the transaction: a batch must commit once or roll back fully.
"""
import copy
import json

from pathforge.db.profile_manager import iso_now
from pathforge.services.ground_truth_correction import artifact_sha256, prepare_correction


class CorrectionActivationError(ValueError):
    """An inactive correction no longer matches its inputs or current storage."""


def validate_package(package):
    if (not isinstance(package, dict) or package.get("state") != "PREPARED_NOT_ACTIVE"
            or package.get("package_version") != 1 or not isinstance(package.get("generation"), dict)):
        raise CorrectionActivationError("An inactive correction package is required")
    contents = {k: v for k, v in package.items() if k != "package_sha256"}
    if artifact_sha256(contents) != package.get("package_sha256"):
        raise CorrectionActivationError("Correction package hash differs")
    rebuilt = prepare_correction({
        "problem": package.get("problem_snapshot"),
        "previous_ground_truth": package.get("previous_artifact"),
        "proposed_response": package.get("proposed_response"),
        "correction_reason": package.get("correction_reason"),
        "generation": {k: package.get("generation", {}).get(k) for k in
                       ("provider", "model", "prompt_version", "generated_at", "finish_reason")},
    })
    for field in ("source_sha256", "previous_sha256", "proposed_response_sha256", "proposed_sha256"):
        if rebuilt[field] != package.get(field):
            raise CorrectionActivationError("Correction inputs changed: " + field)
    if artifact_sha256(package.get("proposed_artifact")) != rebuilt["proposed_sha256"]:
        raise CorrectionActivationError("Proposed storage artifact differs")
    if not any("record_type" not in g for g in rebuilt["proposed_artifact"]["solution_groups"]):
        raise CorrectionActivationError("Revision metadata needs an ordinary solution group")
    return rebuilt


def stage_correction(connection, package, *, apply=False):
    """Preview by default; explicitly stage one UPDATE after locking/checking.

    No commit, generation, automatic retry, schema or user/skill writes. A stale
    snapshot, changed problem source, edited package or rerun fails closed.
    """
    checked = validate_package(package)
    pid = checked["problem_snapshot"]["id"]
    problem = connection.execute(
        "SELECT id, title, title_slug, description FROM problems WHERE id = %s" +
        (" FOR SHARE" if apply else ""), (pid,),
    ).fetchone()
    if problem is None:
        raise CorrectionActivationError("Problem is missing")
    for field, value in checked["problem_snapshot"].items():
        if field in ("id", "title", "title_slug", "description") and problem.get(field) != value:
            raise CorrectionActivationError("Problem source changed: " + field)
    previous = connection.execute(
        "SELECT * FROM problem_ground_truth WHERE problem_id = %s" +
        (" FOR UPDATE" if apply else ""), (pid,),
    ).fetchone()
    if previous is None or artifact_sha256(dict(previous)) != checked["previous_sha256"]:
        raise CorrectionActivationError("Stored ground truth changed; prepare a fresh correction")

    old_groups = previous.get("solution_groups")
    if isinstance(old_groups, str):
        try:
            old_groups = json.loads(old_groups)
        except ValueError:
            old_groups = None  # Malformed old bytes are still archived verbatim.
    versions = [g.get("version", 1) for g in old_groups if isinstance(g, dict)] if isinstance(old_groups, list) else []
    if any(type(version) is not int or version < 1 for version in versions):
        raise CorrectionActivationError("Stored revision versions are unusable")
    version = max(versions, default=1) + 1
    now = iso_now()
    proposed = copy.deepcopy(checked["proposed_artifact"])
    ordinary = [g for g in proposed["solution_groups"] if "record_type" not in g]
    for group in ordinary:
        group["version"] = version
        group["provenance"].append("explicit_ground_truth_correction")
    ordinary[0]["correction_revision"] = {
        "format_version": 1, "version": version, "activated_at": now,
        "package_sha256": package["package_sha256"],
        "source_sha256": checked["source_sha256"],
        "previous_sha256": checked["previous_sha256"],
        "proposed_sha256": checked["proposed_sha256"],
        "previous_artifact": copy.deepcopy(dict(previous)),
        "reason": checked["correction_reason"], "generation": checked["generation"],
    }
    if apply:
        updated = connection.execute(
            "UPDATE problem_ground_truth SET patterns = %s, confidence = %s, "
            "solution_groups = %s::jsonb, validation_status = %s, updated_at = %s "
            "WHERE problem_id = %s RETURNING problem_id",
            (json.dumps(proposed["patterns"]), json.dumps(proposed["confidence"]),
             json.dumps(proposed["solution_groups"], allow_nan=False), "llm_proposed", now, pid),
        ).fetchone()
        if updated is None or updated["problem_id"] != pid:
            raise CorrectionActivationError("Ground-truth update did not return its target")
    return {"problem_id": pid, "version": version, "applied": apply,
            "package_sha256": package["package_sha256"], "previous_sha256": checked["previous_sha256"],
            "artifact": proposed, "updated_at": now}
