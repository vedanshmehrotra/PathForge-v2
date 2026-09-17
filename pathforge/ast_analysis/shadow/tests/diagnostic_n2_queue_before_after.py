"""N2 Batch 1 (RC-N2-1) before/after measurement over the 71-submission corpus.

BEFORE = the HEAD revision of ``fact_extractor.py`` (the only file N2 touches)
AFTER  = the current working tree fact extractor

Everything downstream (techniques / strategies / matching) is shared by both
runs, so the only variable under test is the queue fact extraction change.
The working tree is not modified: the HEAD source is read with ``git show`` and
executed as a standalone module.

Corpus: the union of every ``experiments/code_analysis_evaluation/dataset/*.json``
export, de-duplicated by ``sha256(stripped code)`` — 71 unique real submissions.
Solution groups come from the live DB via ``_load_ground_truth`` (the honest
production view), matching the harness ``--groups-from-db`` mode.

Run: python -m pathforge.ast_analysis.shadow.tests.diagnostic_n2_queue_before_after
"""
import ast
import collections
import glob
import hashlib
import json
import subprocess
import sys
import types

sys.path.insert(0, ".")

from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.ast_analysis.shadow.matching import evaluate_solution_groups
from pathforge.ast_analysis.shadow import fact_extractor as after_fe
from pathforge.services.problem_resolver import _load_ground_truth
from pathforge.db.db import get_connection

SHADOW = "pathforge/ast_analysis/shadow"


def _load_head_module(rel_path: str, name: str):
    src = subprocess.check_output(["git", "show", f"HEAD:{rel_path}"], text=True)
    mod = types.ModuleType(name)
    mod.__file__ = f"HEAD:{rel_path}"
    exec(compile(src, f"HEAD:{rel_path}", "exec"), mod.__dict__)
    return mod


before_fe = _load_head_module(f"{SHADOW}/fact_extractor.py", "n2_before_fact_extractor")


def load_corpus():
    """Union of all dataset exports, de-duplicated by code hash."""
    subs = {}
    for path in glob.glob("experiments/code_analysis_evaluation/dataset/*.json"):
        data = json.load(open(path))
        for s in data.get("submissions", []):
            code = (s.get("code") or s.get("code_text") or "").strip()
            if not code:
                continue
            digest = hashlib.sha256(code.encode()).hexdigest()[:12]
            subs[digest] = {
                "hash": digest,
                "problem_id": s.get("problem_id"),
                "title": s.get("title", ""),
                "code": code,
            }
    return subs


def load_groups(conn, problem_ids):
    cache = {}
    for pid in problem_ids:
        try:
            groups, _ = _load_ground_truth(conn, pid)
        except Exception as exc:  # pragma: no cover - diagnostic only
            print(f"  ! ground truth load failed for {pid}: {exc}")
            groups = []
        cache[pid] = groups or []
    return cache


def evaluate(fe_module, code, groups):
    """Run the shadow pipeline using a specific fact extractor module."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    facts = fe_module.extract_structural_facts(tree)
    techniques = detect_techniques(facts)
    strategies = evaluate_strategies(techniques, facts)
    outcome = None
    if groups:
        outcome = evaluate_solution_groups(groups, techniques, strategies, facts)
    return {
        "facts": facts,
        "fact_types": collections.Counter(f.fact_type for f in facts),
        "queue_ops": sorted(
            {
                f.attributes.get("operation")
                for f in facts
                if f.fact_type == "queue_dequeue"
            }
        ),
        "strategies": {s.strategy_id for s in strategies},
        "outcome": outcome.outcome if outcome else "NO_GROUPS",
        "reasoning": outcome.reasoning if outcome else [],
    }


def main():
    subs = load_corpus()
    print(f"corpus: {len(subs)} unique real submissions")

    conn = get_connection()
    groups_by_pid = load_groups(conn, sorted({s["problem_id"] for s in subs.values()}))
    conn.close()

    before_results = {}
    after_results = {}
    for digest, s in subs.items():
        groups = groups_by_pid.get(s["problem_id"], [])
        before_results[digest] = evaluate(before_fe, s["code"], groups)
        after_results[digest] = evaluate(after_fe, s["code"], groups)

    n = len(subs)

    # ---- strategy-set differences ----
    strategy_changes = []
    fact_changes = []
    verdict_changes = []
    bfs_before = set()
    bfs_after = set()

    for digest, s in subs.items():
        b, a = before_results[digest], after_results[digest]
        if b is None or a is None:
            continue
        if "bfs_shortest_path" in b["strategies"]:
            bfs_before.add(digest)
        if "bfs_shortest_path" in a["strategies"]:
            bfs_after.add(digest)
        if b["strategies"] != a["strategies"]:
            strategy_changes.append((s, b, a))
        if b["fact_types"] != a["fact_types"]:
            fact_changes.append((s, b, a))
        if b["outcome"] != a["outcome"]:
            verdict_changes.append((s, b, a))

    print("\n=== corpus totals ===")
    print(f"  submissions evaluated      : {n}")
    print(f"  bfs_shortest_path BEFORE   : {len(bfs_before)}")
    print(f"  bfs_shortest_path AFTER    : {len(bfs_after)}")
    print(f"  facts changed              : {len(fact_changes)}")
    print(f"  strategy sets changed      : {len(strategy_changes)}")
    print(f"  outcomes changed           : {len(verdict_changes)}")

    print("\n=== fact-level changes (must be queue_dequeue only) ===")
    if not fact_changes:
        print("  none")
    for s, b, a in fact_changes:
        delta = a["fact_types"] - b["fact_types"]
        removed = b["fact_types"] - a["fact_types"]
        print(f"  problem {s['problem_id']} ({s['hash']}) {s['title'][:34]!r}")
        print(f"      added={dict(delta)} removed={dict(removed)}")
        print(f"      queue ops: {b['queue_ops']} -> {a['queue_ops']}")

    print("\n=== strategy-set changes ===")
    if not strategy_changes:
        print("  none")
    for s, b, a in strategy_changes:
        print(f"  problem {s['problem_id']} ({s['hash']}) {s['title'][:34]!r}")
        print(f"      {sorted(b['strategies'])} -> {sorted(a['strategies'])}")

    print("\n=== outcome changes ===")
    if not verdict_changes:
        print("  none")
    for s, b, a in verdict_changes:
        print(f"  problem {s['problem_id']} ({s['hash']}) {s['title'][:34]!r}")
        print(f"      {b['outcome']} -> {a['outcome']}")
        for line in a["reasoning"][:4]:
            print(f"        after: {line}")

    print("\n=== regressions / expectations ===")
    print(f"  bfs gained : {sorted(subs[h]['problem_id'] for h in bfs_after - bfs_before)}")
    print(f"  bfs lost   : {sorted(subs[h]['problem_id'] for h in bfs_before - bfs_after)}")

    before_tally = collections.Counter(
        r["outcome"] for r in before_results.values() if r
    )
    after_tally = collections.Counter(r["outcome"] for r in after_results.values() if r)
    print(f"\n  outcomes BEFORE: {dict(before_tally)}")
    print(f"  outcomes AFTER : {dict(after_tally)}")

    new_confirmed = [
        s for s, b, a in verdict_changes if a["outcome"] == "CONFIRMED"
    ]
    new_contradicted = [
        s for s, b, a in verdict_changes if a["outcome"] == "CONTRADICTED"
    ]
    print(f"\n  new CONFIRMED     : {[(s['problem_id'], s['hash']) for s in new_confirmed]}")
    print(f"  new CONTRADICTED  : {[(s['problem_id'], s['hash']) for s in new_contradicted]}")

    # Any non-bfs strategy set change would be an unexpected side effect.
    unexpected = [
        (s, b, a)
        for s, b, a in strategy_changes
        if (a["strategies"] - b["strategies"]) != {"bfs_shortest_path"}
    ]
    print(f"\n  unexpected non-BFS strategy changes: {len(unexpected)}")
    for s, b, a in unexpected:
        print(f"      problem {s['problem_id']}: {sorted(b['strategies'])} -> {sorted(a['strategies'])}")

    expected = {"exactly_one_strategy_change": len(strategy_changes) == 1,
                "bfs_gained_is_lc102_only": {subs[h]["problem_id"] for h in bfs_after - bfs_before} == {102},
                "no_bfs_losses": not (bfs_before - bfs_after),
                "no_new_contradictions": not new_contradicted,
                "no_non_bfs_strategy_changes": not unexpected,
                "facts_change_is_queue_only": all(
                    set(b["fact_types"] - a["fact_types"]) == set()
                    and set(a["fact_types"] - b["fact_types"]) <= {"queue_dequeue"}
                    for _, b, a in fact_changes
                )}
    print("\n=== expectation checks ===")
    for key, ok in expected.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {key}")


if __name__ == "__main__":
    main()
