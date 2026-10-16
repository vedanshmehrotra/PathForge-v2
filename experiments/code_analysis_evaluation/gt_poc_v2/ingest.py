"""Phase 1 — V2 corpus ingestion.

Combines the committed read-only DB snapshot (from POC v1) with the authored
references, restricted to ``DB_ASSIGNMENT``.

No database access, no network, no LLM.  ``code_text`` is preserved exactly.
"""
import ast
import hashlib
import json
import os

from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.relations import build_relations
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.ast_analysis.shadow.techniques import detect_techniques

from .corpus_authored import AUTHORED_SOLUTIONS, DB_ASSIGNMENT
from .problem_metadata import (
    ALLOWED_SOURCE_TYPES,
    CURATED_PATTERN_SOURCE,
    POC_VERSION,
    PROBLEMS,
    TAXONOMY_VERSION,
)

HERE = os.path.dirname(os.path.abspath(__file__))
_DB_SNAPSHOT_PATH = os.path.join(
    os.path.dirname(HERE), "gt_poc", "corpus_db_snapshot.json"
)

REQUIRED_FIELDS = (
    "solution_id", "problem_id", "source_type", "source_ref",
    "language", "code_text", "raw_hash", "provenance",
    "quality_state", "evidence_state",
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _db_by_id() -> dict:
    with open(_DB_SNAPSHOT_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return {row["db_submission_id"]: row for row in data["solutions"]}


def _classify_evidence(code_text: str) -> str:
    """has_evidence / zero_evidence, observed read-only from the frozen pipeline."""
    try:
        tree = ast.parse(code_text)
    except SyntaxError:
        return "unparseable"
    facts = extract_structural_facts(tree)
    rel = build_relations(tree)
    techs = detect_techniques(facts, rel)
    strats = evaluate_strategies(techs, facts)
    if not techs and not strats:
        return "zero_evidence"
    return "has_evidence"


def _quality_state(source_type: str, verdict) -> str:
    if source_type == "authored":
        return "accepted"
    if verdict == "pass":
        return "accepted"
    if verdict == "fail":
        return "reported_failing"
    return "unverified"


def build_corpus() -> dict:
    db = _db_by_id()
    raw = []
    for problem_id, sub_ids in sorted(DB_ASSIGNMENT.items()):
        for sid in sub_ids:
            row = db[sid]
            raw.append({
                "problem_id": problem_id,
                "source_type": "pathforge_db",
                "source_ref": f"submissions.id={sid}",
                "local_key": f"db_sub_{sid}",
                "code_text": row["code_text"],
                "verdict": row.get("judge_verdict"),
                "provenance": {
                    "kind": "pathforge_submission",
                    "db_submission_id": sid,
                    "judge_verdict": row.get("judge_verdict"),
                    "verdict_type": row.get("verdict_type"),
                    "submitted_at": row.get("submitted_at"),
                    "license": "user-owned",
                },
            })
    for problem_id in sorted(AUTHORED_SOLUTIONS):
        for local_key, code in AUTHORED_SOLUTIONS[problem_id]:
            raw.append({
                "problem_id": problem_id,
                "source_type": "authored",
                "source_ref": (
                    "experiments/code_analysis_evaluation/gt_poc_v2/"
                    f"corpus_authored.py#{local_key}"
                ),
                "local_key": local_key,
                "code_text": code,
                "verdict": None,
                "provenance": {
                    "kind": "authored_reference",
                    "author": "project_author",
                    "license": "project",
                },
            })

    by_problem = {}
    for item in raw:
        by_problem.setdefault(item["problem_id"], []).append(item)

    unknown = sorted(set(by_problem) - set(PROBLEMS))
    if unknown:
        raise ValueError(f"corpus contains problems outside metadata: {unknown}")

    solutions = []
    counter = 0
    for problem_id in sorted(by_problem):
        items = by_problem[problem_id]
        # DB first (by db id), then authored (declared order) — deterministic.
        items = sorted(
            items,
            key=lambda it: (0 if it["source_type"] == "pathforge_db" else 1, it["local_key"]),
        )
        for item in items:
            counter += 1
            solutions.append({
                "solution_id": f"S{counter:04d}",
                "problem_id": item["problem_id"],
                "source_type": item["source_type"],
                "source_ref": item["source_ref"],
                "language": "python",
                "code_text": item["code_text"],
                "raw_hash": sha256_text(item["code_text"]),
                "provenance": item["provenance"],
                "quality_state": _quality_state(item["source_type"], item["verdict"]),
                "evidence_state": _classify_evidence(item["code_text"]),
                "local_key": item["local_key"],
            })
    return {"solutions": solutions}


def validate_corpus(corpus: dict) -> dict:
    solutions = corpus["solutions"]
    problems = {}
    issues = []
    seen_raw = {}
    dup_pairs = []
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
        if sha256_text(s["code_text"]) != s["raw_hash"]:
            issues.append({"solution_id": s["solution_id"], "issue": "raw_hash does not match code_text"})
        problems[s["problem_id"]] = problems.get(s["problem_id"], 0) + 1
        if s["raw_hash"] in seen_raw and seen_raw[s["raw_hash"]]["problem_id"] == s["problem_id"]:
            dup_pairs.append({
                "problem_id": s["problem_id"],
                "raw_hash": s["raw_hash"],
                "duplicate_solution_id": s["solution_id"],
                "duplicate_of": seen_raw[s["raw_hash"]]["solution_id"],
            })
        seen_raw.setdefault(s["raw_hash"], s)

    dist = {}
    for s in solutions:
        dist[s["source_type"]] = dist.get(s["source_type"], 0) + 1
    evidence = {}
    for s in solutions:
        evidence[s["evidence_state"]] = evidence.get(s["evidence_state"], 0) + 1

    problems_with_dup = sorted({d["problem_id"] for d in dup_pairs})

    return {
        "solution_count": len(solutions),
        "problem_count": len(problems),
        "per_problem_counts": {str(k): v for k, v in sorted(problems.items())},
        "source_distribution": dist,
        "evidence_distribution": evidence,
        "duplicate_raw_hash_pairs": dup_pairs,
        "problems_with_D1_duplicates": problems_with_dup,
        "issues": issues,
        "passed": not issues,
    }


def run() -> dict:
    corpus = build_corpus()
    validation = validate_corpus(corpus)
    return {
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
