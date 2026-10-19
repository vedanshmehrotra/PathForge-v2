"""Offline correction packages. No provider, database or activation operations."""
import copy
import hashlib
import json

from pathforge.db.profile_manager import iso_now
from pathforge.services.ground_truth_builder import (
    GroundTruthError, normalize_ground_truth_response, solution_groups_for_storage,
)


class CorrectionPreparationError(ValueError):
    """A local correction request is incomplete or inconsistent."""


def artifact_sha256(value) -> str:
    """Hash the supplied JSON representation, including unknown historical fields."""
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CorrectionPreparationError("Correction inputs must contain valid JSON data") from exc
    return hashlib.sha256(encoded).hexdigest()


def prepare_correction(request: dict) -> dict:
    """Preserve the supplied old artifact and validate a proposed replacement.

    A package is not an active database revision, approval, or correctness
    assertion. Generation details are caller-supplied; unknown values stay null.
    The normal analyzer/preparer never invokes this operation.
    """
    artifact_sha256(request)
    if not isinstance(request, dict):
        raise CorrectionPreparationError("Correction request must be an object")
    operation = request.get("operation", "REPLACE")
    if operation not in ("REPLACE", "RETIRE"):
        raise CorrectionPreparationError("Correction operation must be REPLACE or RETIRE")
    problem = request.get("problem")
    previous = request.get("previous_ground_truth")
    if (not isinstance(problem, dict) or type(problem.get("id")) is not int
            or problem["id"] <= 0 or not isinstance(previous, dict)):
        raise CorrectionPreparationError("Problem and previous ground-truth snapshot are required")
    if type(previous.get("problem_id")) is not int or previous["problem_id"] != problem["id"]:
        raise CorrectionPreparationError("Previous snapshot must belong to the same problem")
    if any(problem.get(field) is not None and not isinstance(problem[field], str)
           for field in ("description", "title", "title_slug")):
        raise CorrectionPreparationError("Problem source fields must be strings or null")
    source = problem.get("description") or problem.get("title")
    if not isinstance(source, str) or not source.strip():
        raise CorrectionPreparationError("The supplied problem needs a description or title")
    reason = request.get("correction_reason")
    if not isinstance(reason, str) or not reason.strip():
        raise CorrectionPreparationError("An explicit correction reason is required")
    generation = request.get("generation")
    if generation is None:
        generation = {}
    allowed = ("provider", "model", "prompt_version", "generated_at", "finish_reason")
    if (not isinstance(generation, dict) or set(generation) - set(allowed)
            or any(value is not None and (not isinstance(value, str) or not value.strip())
                   for value in generation.values())):
        raise CorrectionPreparationError("Generation metadata accepts only documented nonempty strings or null")
    if generation.get("finish_reason") not in (None, "stop"):
        raise CorrectionPreparationError("Incomplete or failed generation cannot prepare a correction")

    raw = request.get("proposed_response")
    if operation == "RETIRE":
        if raw is not None:
            raise CorrectionPreparationError("Retirement must not contain a replacement proposal")
        patterns, confidence, groups = [], {}, []
    else:
        patterns, confidence, approaches = normalize_ground_truth_response(raw)
        if not approaches:
            raise CorrectionPreparationError("A correction must explicitly declare its proposed approaches")
        groups = solution_groups_for_storage(problem["id"], patterns, confidence, approaches,
                                            source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest())
        if not groups:
            raise GroundTruthError("Ground truth correction failed: no usable listed groups")
    proposed = {"problem_id": problem["id"], "patterns": patterns, "confidence": confidence,
                "solution_groups": groups,
                "validation_status": "unobserved" if operation == "RETIRE" else "llm_proposed"}
    # Construct from builder output, never overlay the old row's approval fields.
    package = {
        "package_version": 1, "state": "PREPARED_NOT_ACTIVE", "operation": operation,
        "prepared_at": iso_now(),
        "problem_snapshot": copy.deepcopy(problem),
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "previous_artifact": copy.deepcopy(previous), "previous_sha256": artifact_sha256(previous),
        "proposed_response": copy.deepcopy(raw), "proposed_response_sha256": artifact_sha256(raw),
        "proposed_artifact": proposed, "proposed_sha256": artifact_sha256(proposed),
        "correction_reason": reason.strip(),
        "generation": {**{key: generation.get(key) for key in allowed},
                       "metadata_source": "caller_supplied_not_independently_verified"},
        "limitations": ["Shape and vocabulary validation do not establish algorithmic suitability or exhaustive coverage.",
                        "This package does not activate a revision, grant authority or update historical skills."],
    }
    uncovered = sorted({pattern for group in groups for pattern in group.get("unmapped_patterns", [])})
    if uncovered:
        package["limitations"].append("Canonical coverage is unavailable for: " + ", ".join(uncovered))
    package["package_sha256"] = artifact_sha256(package)
    return package
