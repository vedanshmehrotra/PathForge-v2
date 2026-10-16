"""M1+M2 architecture-hardening before/after measurement over the full corpus.

BEFORE = HEAD pipeline: HEAD ``fact_extractor.py`` + HEAD ``techniques.py``
         (relations did not exist at HEAD).
AFTER  = current working tree: current fact extractor + current techniques
         + the M2 relations layer wired exactly as ``shadow_runner`` wires it
         (``build_relations(tree)`` -> ``detect_techniques(facts, relations)``).

Strategies and matching are unchanged by M1+M2, so both runs share the current
``strategies.py`` / ``matching.py``. The working tree is not modified: HEAD
sources are read with ``git show`` and executed as standalone modules that
import the (unchanged) data structures.

Corpus: the union of every ``experiments/code_analysis_evaluation/dataset/*.json``
export, de-duplicated by ``sha256(stripped code)``. Solution groups come from
the live DB via ``_load_ground_truth`` (the honest production view), matching
the harness ``--groups-from-db`` mode.

Fact comparison is order-independent: M1 unifies operation detection into a
single dispatch point, which can legitimately change *emission order* (and
therefore fact_id numbering) without changing any fact's type/attributes.
A verdict change from fact-order alone would be a genuine finding — the
diagnostic therefore compares fact *sets* and separately reports whether any
downstream evidence depends on the ordering.

Run: python -m pathforge.ast_analysis.shadow.tests.diagnostic_m1_m2_before_after
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

from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.relations import build_relations
from pathforge.ast_analysis.shadow.techniques import detect_techniques as after_tech
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.ast_analysis.shadow.matching import evaluate_solution_groups
from pathforge.services.problem_resolver import _load_ground_truth
from pathforge.db.db import get_connection

SHADOW = "pathforge/ast_analysis/shadow"


def _load_head_module(rel_path: str, name: str):
    src = subprocess.check_output(["git", "show", f"HEAD:{rel_path}"], text=True)
    mod = types.ModuleType(name)
    mod.__file__ = f"HEAD:{rel_path}"
    exec(compile(src, f"HEAD:{rel_path}", "exec"), mod.__dict__)
    return mod


head_fe = _load_head_module(f"{SHADOW}/fact_extractor.py", "m1m2_before_fact_extractor")
head_tech = _load_head_module(f"{SHADOW}/techniques.py", "m1m2_before_techniques")


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


def fact_signature(facts):
    """Order-independent fact fingerprint: (type, attributes) multiset."""
    return collections.Counter(
        (f.fact_type, json.dumps(f.attributes, sort_keys=True)) for f in facts
    )


def evaluate_before(code, groups):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    facts = head_fe.extract_structural_facts(tree)
    techniques = head_tech.detect_techniques(facts)
    strategies = evaluate_strategies(techniques, facts)
    outcome = None
    if groups:
        outcome = evaluate_solution_groups(groups, techniques, strategies, facts)
    return {
        "fact_sig": fact_signature(facts),
        "n_facts": len(facts),
        "techniques": {t.technique_id: tuple(t.supporting_fact_ids) for t in techniques},
        "strategies": {s.strategy_id for s in strategies},
        "outcome": outcome.outcome if outcome else "NO_GROUPS",
        "reasoning": outcome.reasoning if outcome else [],
    }


def evaluate_after(code, groups):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    # Wired exactly as shadow_runner wires the pipeline.
    tree2 = ast.parse(code)
    relations = build_relations(tree2)
    facts = extract_structural_facts(tree)
    techniques = after_tech(facts, relations=relations)
    strategies = evaluate_strategies(techniques, facts)
    outcome = None
    if groups:
        outcome = evaluate_solution_groups(groups, techniques, strategies, facts)
    return {
        "fact_sig": fact_signature(facts),
        "n_facts": len(facts),
        "techniques": {t.technique_id: tuple(t.supporting_fact_ids) for t in techniques},
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
        before_results[digest] = evaluate_before(s["code"], groups)
        after_results[digest] = evaluate_after(s["code"], groups)

    fact_changes = []
    tech_changes = []
    strategy_changes = []
    verdict_changes = []

    for digest, s in subs.items():
        b, a = before_results[digest], after_results[digest]
        if b is None or a is None:
            continue
        if b["fact_sig"] != a["fact_sig"]:
            fact_changes.append((s, b, a))
        if b["techniques"] != a["techniques"]:
            tech_changes.append((s, b, a))
        if b["strategies"] != a["strategies"]:
            strategy_changes.append((s, b, a))
        if b["outcome"] != a["outcome"]:
            verdict_changes.append((s, b, a))

    n = len(subs)
    print("\n=== corpus totals ===")
    print(f"  submissions evaluated : {n}")
    print(f"  fact multisets changed: {len(fact_changes)}")
    print(f"  technique maps changed: {len(tech_changes)}")
    print(f"  strategy sets changed : {len(strategy_changes)}")
    print(f"  outcomes changed      : {len(verdict_changes)}")

    for label, changes, key in (
        ("fact-level", fact_changes, "fact_sig"),
        ("technique", tech_changes, "techniques"),
        ("strategy-set", strategy_changes, "strategies"),
        ("outcome", verdict_changes, "outcome"),
    ):
        print(f"\n=== {label} changes ===")
        if not changes:
            print("  none")
        for s, b, a in changes:
            print(f"  problem {s['problem_id']} ({s['hash']}) {s['title'][:34]!r}")
            if label == "fact-level":
                added = a["fact_sig"] - b["fact_sig"]
                removed = b["fact_sig"] - a["fact_sig"]
                print(f"      added  = {dict(added)}")
                print(f"      removed= {dict(removed)}")
            elif label == "technique":
                ids = set(b) | set(a)
                for tid in sorted(ids):
                    if b.get(tid) != a.get(tid):
                        print(f"      {tid}: {b.get(tid)} -> {a.get(tid)}")
            else:
                print(f"      {b[key]} -> {a[key]}")
            if label == "outcome":
                for line in a["reasoning"][:4]:
                    print(f"        after: {line}")

    before_tally = collections.Counter(
        r["outcome"] for r in before_results.values() if r
    )
    after_tally = collections.Counter(
        r["outcome"] for r in after_results.values() if r
    )
    print(f"\n  outcomes BEFORE: {dict(before_tally)}")
    print(f"  outcomes AFTER : {dict(after_tally)}")

    new_confirmed = [s for s, b, a in verdict_changes if a["outcome"] == "CONFIRMED"]
    new_contradicted = [s for s, b, a in verdict_changes if a["outcome"] == "CONTRADICTED"]
    print(f"\n  new CONFIRMED    : {[(s['problem_id'], s['hash']) for s in new_confirmed]}")
    print(f"  new CONTRADICTED : {[(s['problem_id'], s['hash']) for s in new_contradicted]}")

    # Any technique-map change not caused by a legitimate fact change would
    # indicate the relations oracle diverged from the fallback.
    tech_change_without_fact_change = [
        (s, b, a)
        for s, b, a in tech_changes
        if b["fact_sig"] == a["fact_sig"]
    ]
    print(f"\n  technique changes with identical facts: {len(tech_change_without_fact_change)}")
    for s, b, a in tech_change_without_fact_change:
        print(f"      problem {s['problem_id']}: {b['techniques']} -> {a['techniques']}")

    expected = {
        "no_contradictions": not new_contradicted,
        "no_technique_change_without_fact_change": not tech_change_without_fact_change,
    }
    print("\n=== expectation checks ===")
    for key, ok in expected.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {key}")


if __name__ == "__main__":
    main()
