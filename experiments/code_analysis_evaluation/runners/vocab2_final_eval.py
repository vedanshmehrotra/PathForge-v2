"""FINAL Vocabulary Layer 2 evaluation over the independent 301-case corpus.

Evaluation-only harness (not production code, not imported by pathforge).
Runs the FROZEN shadow pipeline (facts -> techniques -> strategies ->
group satisfaction) over the 301 disjoint benchmark cases and computes
per-family TP/FP/FN/TN under an explicit, documented label bridge:

- Benchmark labels are V0 pattern names (e.g. ``prefix_sum``).
- ``PATTERN_TO_V1_MAPPING`` maps each labeled pattern to V1 concepts
  (the production vocabulary). A pattern maps to >=1 concepts; the
  FIRST listed required concept is used as the family's primary
  benchmark concept when a single concept must be named.
- For a POSITIVE case: the required concepts of the labeled pattern's
  mapping must ALL be detected by the frozen pipeline for a TP. If any
  is missing -> FN (with the missing concept recorded).
- For a NEGATIVE case (is_positive=False, confusable pair): the case
  is a TN if NONE of the labeled pattern's required concepts are
  detected, and an FP if any of them is.

No thresholds or detectors are tuned here; the pipeline is run exactly
as shipped (with the shared relation layer, matching the shadow runner).

Outputs (written next to this file, under ../results/vocab2_final_eval/):
- disjoint301_eval_results.json  (per-case records + summary metrics)
- disjoint301_eval_summary.txt   (human-readable summary)
"""
import ast
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

from pathforge.ast_analysis.shadow.fact_extractor import extract_structural_facts
from pathforge.ast_analysis.shadow.relations import build_relations
from pathforge.ast_analysis.shadow.techniques import detect_techniques
from pathforge.ast_analysis.shadow.strategies import evaluate_strategies
from pathforge.services.ground_truth_builder import PATTERN_TO_V1_MAPPING


def load_cases():
    mods = [
        "src.ast_detection.semantic.disjoint_corpus",
        "src.ast_detection.semantic.disjoint_corpus_extra",
        "src.ast_detection.semantic.disjoint_corpus_extra2",
        "src.ast_detection.semantic.disjoint_corpus_extra3",
        "src.ast_detection.semantic.disjoint_corpus_final",
    ]
    import importlib
    cases = []
    for m in mods:
        mod = importlib.import_module(m)
        for fn in [f for f in dir(mod) if f.startswith("build")]:
            res = getattr(mod, fn)()
            if isinstance(res, list) and len(res) > 3:
                cases.extend(res)
    return cases


def required_concepts_for(pattern: str):
    mapping = PATTERN_TO_V1_MAPPING.get(pattern)
    if mapping is None:
        return None
    return list(mapping.get("required") or [])


def run_case(code: str):
    tree = ast.parse(code)
    facts = extract_structural_facts(tree)
    relations = build_relations(tree)
    techs = detect_techniques(facts, relations)
    strats = evaluate_strategies(techs, facts)
    return {
        "techniques": sorted({t.technique_id for t in techs}),
        "strategies": sorted({s.strategy_id for s in strats}),
        "fact_types": sorted({f.fact_type for f in facts}),
    }


def detected_concepts(res: dict):
    """V1 concepts detected by the pipeline = techniques + strategies.

    ``PATTERN_TO_V1_MAPPING.required`` entries may be either a technique
    (e.g. ``hash_lookup``) or a strategy (e.g. ``two_pointers_opposite``);
    the production matcher satisfies groups against both namespaces, so
    the benchmark bridge must too.
    """
    return set(res["techniques"]) | set(res["strategies"])


def main():
    cases = load_cases()
    assert len(cases) == 301, f"expected 301 cases, got {len(cases)}"

    per_case = []
    for c in cases:
        req = required_concepts_for(c.expected_pattern)
        try:
            res = run_case(c.code)
            parse_error = False
        except SyntaxError as e:
            res = {"techniques": [], "strategies": [], "fact_types": []}
            parse_error = True

        detected = detected_concepts(res)
        if req is None:
            verdict = "UNMAPPED_LABEL"
            missing = []
        else:
            missing = [r for r in req if r not in detected]
            if c.is_positive:
                verdict = "TP" if not missing else "FN"
            else:
                verdict = "FP" if any(r in detected for r in req) else "TN"

        per_case.append({
            "name": c.name,
            "family": c.family,
            "expected_pattern": c.expected_pattern,
            "is_positive": c.is_positive,
            "required_concepts": req,
            "missing_concepts": missing,
            "verdict": verdict,
            "parse_error": parse_error,
            "notes": c.notes,
            "code": c.code,
            "detected_techniques": res["techniques"],
            "detected_strategies": res["strategies"],
            "fact_types": res["fact_types"],
        })

    # ---- metrics per labeled pattern ----
    metrics = {}
    by_pattern = collections.defaultdict(list)
    for r in per_case:
        by_pattern[r["expected_pattern"]].append(r)
    for pattern, rs in sorted(by_pattern.items()):
        tp = sum(1 for r in rs if r["verdict"] == "TP")
        fp = sum(1 for r in rs if r["verdict"] == "FP")
        fn = sum(1 for r in rs if r["verdict"] == "FN")
        tn = sum(1 for r in rs if r["verdict"] == "TN")
        n = len(rs)
        precision = tp / (tp + fp) if (tp + fp) else None
        recall = tp / (tp + fn) if (tp + fn) else None
        f1 = (2 * precision * recall / (precision + recall)
              if precision is not None and recall is not None
              and (precision + recall) else None)
        metrics[pattern] = {
            "n": n, "positives": sum(1 for r in rs if r["is_positive"]),
            "negatives": sum(1 for r in rs if not r["is_positive"]),
            "TP": tp, "FP": fp, "FN": fn, "TN": tn,
            "precision": precision, "recall": recall, "f1": f1,
        }

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "results", "vocab2_final_eval")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "disjoint301_eval_results.json"), "w") as fh:
        json.dump({"metrics": metrics, "records": per_case}, fh, indent=2)

    with open(os.path.join(out_dir, "disjoint301_eval_summary.txt"), "w") as fh:
        fh.write("301-case disjoint corpus — frozen shadow pipeline\n")
        fh.write("=" * 60 + "\n\n")
        fh.write(f"{'pattern':28} {'n':>4} {'pos':>4} {'neg':>4} "
                 f"{'TP':>4} {'FP':>4} {'FN':>4} {'TN':>4} "
                 f"{'prec':>6} {'rec':>6} {'f1':>6}\n")
        for p, m in sorted(metrics.items(), key=lambda kv: -kv[1]["n"]):
            prec = f"{m['precision']:.3f}" if m["precision"] is not None else "-"
            rec = f"{m['recall']:.3f}" if m["recall"] is not None else "-"
            f1 = f"{m['f1']:.3f}" if m["f1"] is not None else "-"
            fh.write(f"{p:28} {m['n']:>4} {m['positives']:>4} {m['negatives']:>4} "
                     f"{m['TP']:>4} {m['FP']:>4} {m['FN']:>4} {m['TN']:>4} "
                     f"{prec:>6} {rec:>6} {f1:>6}\n")
        tp = sum(m["TP"] for m in metrics.values())
        fp = sum(m["FP"] for m in metrics.values())
        fn = sum(m["FN"] for m in metrics.values())
        tn = sum(m["TN"] for m in metrics.values())
        unmapped = sum(1 for r in per_case if r["verdict"] == "UNMAPPED_LABEL")
        fh.write(f"\nTOTAL  TP={tp}  FP={fp}  FN={fn}  TN={tn}  "
                 f"UNMAPPED_LABEL={unmapped}\n")

    print("wrote", os.path.join(out_dir, "disjoint301_eval_results.json"))
    print("wrote", os.path.join(out_dir, "disjoint301_eval_summary.txt"))

    # console summary
    print()
    for p, m in sorted(metrics.items(), key=lambda kv: -kv[1]["n"]):
        prec = f"{m['precision']:.3f}" if m["precision"] is not None else "-"
        rec = f"{m['recall']:.3f}" if m["recall"] is not None else "-"
        f1 = f"{m['f1']:.3f}" if m["f1"] is not None else "-"
        print(f"{p:28} n={m['n']:>3} TP={m['TP']:>3} FP={m['FP']:>3} "
              f"FN={m['FN']:>3} TN={m['TN']:>3} P={prec} R={rec} F1={f1}")


if __name__ == "__main__":
    main()
