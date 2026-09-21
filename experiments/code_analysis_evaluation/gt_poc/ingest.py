"""Phase 1 — corpus ingestion.

Combines the committed read-only DB snapshot (``corpus_db_snapshot.json``) with
the authored references (``corpus_authored.py``) into ``reference_solutions.json``.

No database access, no network, no LLM.  ``code_text`` is preserved exactly.
"""
import ast
import json
import os

from .core import sha256_hex
from .problem_metadata import (
    ALLOWED_SOURCE_TYPES,
    CURATED_PATTERN_SOURCE,
    POC_VERSION,
    PROBLEMS,
    TAXONOMY_VERSION,
)

HERE = os.path.dirname(os.path.abspath(__file__))

_DB_SNAPSHOT_PATH = os.path.join(HERE, "corpus_db_snapshot.json")

REQUIRED_FIELDS = (
    "solution_id", "problem_id", "source_type", "source_ref",
    "language", "code_text", "raw_hash", "provenance",
)


def _load_db_snapshot() -> list:
    with open(_DB_SNAPSHOT_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    out = []
    for row in data["solutions"]:
        out.append({
            "problem_id": row["problem_id"],
            "source_type": "pathforge_db",
            "source_ref": f"submissions.id={row['db_submission_id']}",
            "local_key": f"db_sub_{row['db_submission_id']}",
            "code_text": row["code_text"],
            "provenance": {
                "kind": "pathforge_submission",
                "db_submission_id": row["db_submission_id"],
                "judge_verdict": row.get("judge_verdict"),
                "verdict_type": row.get("verdict_type"),
                "submitted_at": row.get("submitted_at"),
                "license": "user-owned",
            },
        })
    return out


def _load_authored():
    from .corpus_authored import AUTHORED_SOLUTIONS
    out = []
    for problem_id in sorted(AUTHORED_SOLUTIONS):
        for local_key, code in AUTHORED_SOLUTIONS[problem_id]:
            out.append({
                "problem_id": problem_id,
                "source_type": "authored",
                "source_ref": f"experiments/code_analysis_evaluation/gt_poc/corpus_authored.py#{local_key}",
                "local_key": local_key,
                "code_text": code,
                "provenance": {
                    "kind": "authored_reference",
                    "author": "project_author",
                    "license": "project",
                },
            })
    return out


def build_corpus() -> dict:
    """Assemble the deterministic corpus (DB snapshot first, then authored)."""
    raw = []
    db = _load_db_snapshot()
    authored = _load_authored()
    by_problem = {}
    for item in db + authored:
        by_problem.setdefault(item["problem_id"], []).append(item)

    unknown = sorted(set(by_problem) - set(PROBLEMS))
    if unknown:
        raise ValueError(f"corpus contains problems outside POC metadata: {unknown}")

    solutions = []
    counter = 0
    for problem_id in sorted(by_problem):
        # DB solutions first (by db id, already ordered), then authored (declared order)
        items = by_problem[problem_id]
        items = sorted(
            items,
            key=lambda it: (0 if it["source_type"] == "pathforge_db" else 1, it["local_key"]),
        )
        for item in items:
            counter += 1
            solution_id = f"S{counter:04d}"
            solutions.append({
                "solution_id": solution_id,
                "problem_id": item["problem_id"],
                "source_type": item["source_type"],
                "source_ref": item["source_ref"],
                "language": "python",
                "code_text": item["code_text"],
                "raw_hash": sha256_hex(item["code_text"]),
                "provenance": item["provenance"],
                "local_key": item["local_key"],
            })
    return {"solutions": solutions}


def validate_corpus(corpus: dict) -> dict:
    """Phase 1 checks: metadata, provenance, source type, hashes, code fidelity."""
    solutions = corpus["solutions"]
    problems = {}
    issues = []
    seen_raw = {}
    hash_collisions = []
    for s in solutions:
        for field in REQUIRED_FIELDS:
            if not s.get(field):
                issues.append({"solution_id": s.get("solution_id"), "issue": f"missing field {field}"})
        if s["source_type"] not in ALLOWED_SOURCE_TYPES:
            issues.append({"solution_id": s["solution_id"], "issue": f"disallowed source_type {s['source_type']}"})
        if s["language"] != "python":
            issues.append({"solution_id": s["solution_id"], "issue": f"unexpected language {s['language']}"})
        try:
            ast.parse(s["code_text"])
        except SyntaxError as exc:
            issues.append({"solution_id": s["solution_id"], "issue": f"syntax error: {exc}"})
        # code fidelity: the hash must match the stored text exactly
        if sha256_hex(s["code_text"]) != s["raw_hash"]:
            issues.append({"solution_id": s["solution_id"], "issue": "raw_hash does not match code_text"})
        problems[s["problem_id"]] = problems.get(s["problem_id"], 0) + 1
        if s["raw_hash"] in seen_raw and seen_raw[s["raw_hash"]]["problem_id"] == s["problem_id"]:
            hash_collisions.append({
                "raw_hash": s["raw_hash"],
                "solution_id": s["solution_id"],
                "duplicate_of": seen_raw[s["raw_hash"]]["solution_id"],
            })
        seen_raw.setdefault(s["raw_hash"], s)

    dist = {}
    for s in solutions:
        dist[s["source_type"]] = dist.get(s["source_type"], 0) + 1

    return {
        "solution_count": len(solutions),
        "problem_count": len(problems),
        "per_problem_counts": {str(k): v for k, v in sorted(problems.items())},
        "source_distribution": dist,
        "duplicate_raw_hashes": hash_collisions,
        "issues": issues,
        "passed": not issues,
    }


def run() -> dict:
    corpus = build_corpus()
    validation = validate_corpus(corpus)
    artifact = {
        "poc_version": POC_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "curated_pattern_source": CURATED_PATTERN_SOURCE,
        "phase": "1_ingestion",
        "ingestion": validation,
        "problems": {
            str(pid): {
                "title": PROBLEMS[pid]["title"],
                "difficulty": PROBLEMS[pid]["difficulty"],
                "curated_patterns": PROBLEMS[pid]["curated_patterns"],
            }
            for pid in sorted(PROBLEMS)
        },
        "solutions": corpus["solutions"],
    }
    return artifact


def write_artifact(artifact: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2, sort_keys=False)
        fh.write("\n")
