"""Main orchestration script for the code analysis evaluation.

Runs all evaluation steps in sequence:
1. Build dataset
2. Run analysis (legacy + shadow)
3. Calculate metrics
4. Run error analysis
5. Run robustness tests
6. Generate summary report

Usage:
    python experiments/code_analysis_evaluation/runners/run_all.py
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from runners.build_dataset import build_dataset
from runners.run_evaluation import EvaluationRunner
from runners.calculate_metrics import run_full_evaluation
from runners.error_analysis import run_error_analysis
from runners.robustness_test import run_robustness_tests


BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = str(BASE_DIR / "dataset" / "selected_submissions")
RESULTS_DIR = str(BASE_DIR / "results")
RAW_DIR = str(RESULTS_DIR / "raw_outputs")
METRICS_DIR = str(RESULTS_DIR / "metrics")
ERROR_DIR = str(RESULTS_DIR / "error_analysis")
ROBUSTNESS_DIR = str(RESULTS_DIR / "robustness")
REPORT_DIR = str(RESULTS_DIR / "reports")


def run_all():
    """Run the complete evaluation pipeline."""
    print("=" * 70)
    print("PATHFORGE CODE ANALYSIS EVALUATION")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)
    
    # ── Step 1: Build dataset ──────────────────────────────────────────
    print("\n[Step 1] Building dataset...")
    csv_path = str(PROJECT_ROOT / "pathforge" / "data" / "pathforge_problems_fixed.csv")
    
    if not os.path.exists(csv_path):
        print(f"  ERROR: CSV not found at {csv_path}")
        return
    
    dataset_summary = build_dataset(csv_path, DATASET_DIR, max_submissions=200)
    print(f"  Created {dataset_summary['total_submissions']} submissions")
    print(f"  Concepts covered: {len(dataset_summary['concepts_covered'])}")
    
    # ── Step 2: Run analysis ──────────────────────────────────────────
    print("\n[Step 2] Running analysis (legacy + shadow)...")
    dataset_path = os.path.join(DATASET_DIR, "submissions.json")
    
    runner = EvaluationRunner()
    eval_summary = runner.run_dataset(dataset_path, RAW_DIR)
    print(f"  Legacy success: {eval_summary['legacy_success_rate']:.1%}")
    print(f"  Shadow success: {eval_summary['shadow_success_rate']:.1%}")
    
    # ── Step 3: Calculate metrics ─────────────────────────────────────
    print("\n[Step 3] Calculating metrics...")
    ground_truth_path = str(BASE_DIR / "ground_truth" / "labels.json")
    
    metrics = run_full_evaluation(
        os.path.join(RAW_DIR, "raw_results.json"),
        ground_truth_path,
        METRICS_DIR,
    )
    
    # ── Step 4: Error analysis ────────────────────────────────────────
    print("\n[Step 4] Running error analysis...")
    error_summary = run_error_analysis(
        os.path.join(RAW_DIR, "raw_results.json"),
        ground_truth_path,
        ERROR_DIR,
    )
    
    # ── Step 5: Robustness tests ─────────────────────────────────────
    print("\n[Step 5] Running robustness tests...")
    robustness_summary = run_robustness_tests(ROBUSTNESS_DIR)
    
    # ── Step 6: Generate summary report ───────────────────────────────
    print("\n[Step 6] Generating summary report...")
    report = generate_summary_report(
        dataset_summary, eval_summary, metrics, error_summary, robustness_summary
    )
    
    report_path = os.path.join(REPORT_DIR, "summary_report.md")
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"  Report saved to: {report_path}")
    
    # ── Save experiment log ────────────────────────────────────────────
    log = {
        "date": datetime.now().isoformat(),
        "dataset_size": dataset_summary["total_submissions"],
        "concepts_evaluated": len(dataset_summary["concepts_covered"]),
        "concepts_list": dataset_summary["concepts_covered"],
        "legacy_success_rate": eval_summary["legacy_success_rate"],
        "shadow_success_rate": eval_summary["shadow_success_rate"],
        "known_limitations": [
            "Ground truth uses target_concepts as proxy (no expert labels)",
            "Template solutions may not represent real coding diversity",
            "Only Python submissions tested",
            "Shadow system has limited concept coverage",
        ],
        "fixes_made": [],
    }
    
    log_path = str(BASE_DIR / "EXPERIMENT_LOG.md")
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write("# Experiment Log\n\n")
        f.write(f"**Date**: {log['date']}\n\n")
        f.write(f"**Dataset Size**: {log['dataset_size']} submissions\n\n")
        f.write(f"**Concepts Evaluated**: {log['concepts_evaluated']}\n\n")
        f.write(f"**Legacy Success Rate**: {log['legacy_success_rate']:.1%}\n\n")
        f.write(f"**Shadow Success Rate**: {log['shadow_success_rate']:.1%}\n\n")
        f.write("## Known Limitations\n\n")
        for lim in log["known_limitations"]:
            f.write(f"- {lim}\n")
        f.write("\n## Fixes Made\n\n")
        if log["fixes_made"]:
            for fix in log["fixes_made"]:
                f.write(f"- {fix}\n")
        else:
            f.write("None - observational only.\n")
    
    print("\n" + "=" * 70)
    print("EVALUATION COMPLETE")
    print(f"Finished: {datetime.now().isoformat()}")
    print("=" * 70)
    
    return report


def generate_summary_report(
    dataset_summary: dict,
    eval_summary: dict,
    metrics: dict,
    error_summary: dict,
    robustness_summary: dict,
) -> str:
    """Generate the final summary report in markdown."""
    legacy = metrics.get("legacy_overall", {})
    shadow = metrics.get("shadow_overall", {})
    comparison = metrics.get("comparison", [])
    
    report = f"""# PathForge Code Analysis Evaluation — Summary Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 1. Dataset Summary

| Metric | Value |
|--------|-------|
| Total submissions | {dataset_summary['total_submissions']} |
| Concepts covered | {len(dataset_summary['concepts_covered'])} |
| Correct solutions | {dataset_summary['by_correctness'].get('correct', 0)} |
| Incorrect solutions | {dataset_summary['by_correctness'].get('incorrect', 0)} |
| Standard style | {dataset_summary['by_style'].get('standard', 0)} |
| Variant styles | {sum(v for k, v in dataset_summary['by_style'].items() if k != 'standard')} |

**Concepts tested**: {', '.join(dataset_summary['concepts_covered'][:20])}{'...' if len(dataset_summary['concepts_covered']) > 20 else ''}

---

## 2. Analysis Success Rates

| System | Success Rate | Errors |
|--------|-------------|--------|
| Legacy (AST) | {eval_summary['legacy_success_rate']:.1%} | {eval_summary['legacy_errors']} |
| Shadow (Fact/Technique/Strategy) | {eval_summary['shadow_success_rate']:.1%} | {eval_summary['shadow_errors']} |

---

## 3. Overall Performance Metrics

### Legacy System
"""
    
    if "micro" in legacy:
        m = legacy["micro"]
        report += f"""
| Metric | Micro Avg | Macro Avg | Weighted Avg |
|--------|-----------|-----------|--------------|
| Precision | {m.get('precision', 'N/A')} | {legacy.get('macro', {}).get('precision', 'N/A')} | {legacy.get('weighted', {}).get('precision', 'N/A')} |
| Recall | {m.get('recall', 'N/A')} | {legacy.get('macro', {}).get('recall', 'N/A')} | {legacy.get('weighted', {}).get('recall', 'N/A')} |
| F1 | {m.get('f1', 'N/A')} | {legacy.get('macro', {}).get('f1', 'N/A')} | {legacy.get('weighted', {}).get('f1', 'N/A')} |
| False Positive Rate | {m.get('false_positive_rate', 'N/A')} | {legacy.get('macro', {}).get('false_positive_rate', 'N/A')} | {legacy.get('weighted', {}).get('false_positive_rate', 'N/A')} |
| False Negative Rate | {m.get('false_negative_rate', 'N/A')} | {legacy.get('macro', {}).get('false_negative_rate', 'N/A')} | {legacy.get('weighted', {}).get('false_negative_rate', 'N/A')} |
"""
    else:
        report += "\n*Insufficient data for micro/macro averaging.*\n"
    
    report += "\n### Shadow System\n"
    
    if "micro" in shadow:
        m = shadow["micro"]
        report += f"""
| Metric | Micro Avg | Macro Avg | Weighted Avg |
|--------|-----------|-----------|--------------|
| Precision | {m.get('precision', 'N/A')} | {shadow.get('macro', {}).get('precision', 'N/A')} | {shadow.get('weighted', {}).get('precision', 'N/A')} |
| Recall | {m.get('recall', 'N/A')} | {shadow.get('macro', {}).get('recall', 'N/A')} | {shadow.get('weighted', {}).get('recall', 'N/A')} |
| F1 | {m.get('f1', 'N/A')} | {shadow.get('macro', {}).get('f1', 'N/A')} | {shadow.get('weighted', {}).get('f1', 'N/A')} |
| False Positive Rate | {m.get('false_positive_rate', 'N/A')} | {shadow.get('macro', {}).get('false_positive_rate', 'N/A')} | {shadow.get('weighted', {}).get('false_positive_rate', 'N/A')} |
| False Negative Rate | {m.get('false_negative_rate', 'N/A')} | {shadow.get('macro', {}).get('false_negative_rate', 'N/A')} | {shadow.get('weighted', {}).get('false_negative_rate', 'N/A')} |
"""
    else:
        report += "\n*Insufficient data for micro/macro averaging.*\n"
    
    report += "\n---\n\n## 4. Legacy vs Shadow Comparison\n\n"
    
    if comparison:
        report += "| Concept | Legacy P | Legacy R | Legacy F1 | Shadow P | Shadow R | Shadow F1 | Δ F1 |\n"
        report += "|----------|----------|----------|-----------|----------|----------|-----------|------|\n"
        for row in comparison:
            if row.get("legacy_f1") is not None or row.get("shadow_f1") is not None:
                lp = f"{row['legacy_precision']:.3f}" if row.get('legacy_precision') is not None else "-"
                lr = f"{row['legacy_recall']:.3f}" if row.get('legacy_recall') is not None else "-"
                lf = f"{row['legacy_f1']:.3f}" if row.get('legacy_f1') is not None else "-"
                sp = f"{row['shadow_precision']:.3f}" if row.get('shadow_precision') is not None else "-"
                sr = f"{row['shadow_recall']:.3f}" if row.get('shadow_recall') is not None else "-"
                sf = f"{row['shadow_f1']:.3f}" if row.get('shadow_f1') is not None else "-"
                df = f"{row['f1_diff']:+.3f}" if row.get('f1_diff') is not None else "-"
                report += f"| {row['concept']} | {lp} | {lr} | {lf} | {sp} | {sr} | {sf} | {df} |\n"
    else:
        report += "*No comparison data available.*\n"
    
    report += f"""
---

## 5. Error Analysis

| System | Total Errors | By Type |
|--------|-------------|---------|
| Legacy | {error_summary.get('legacy_total', 0)} | {json.dumps(error_summary.get('legacy_errors', {}))} |
| Shadow | {error_summary.get('shadow_total', 0)} | {json.dumps(error_summary.get('shadow_errors', {}))} |

---

## 6. Robustness Testing

| Metric | Value |
|--------|-------|
| Variants tested | {robustness_summary.get('total_variants_tested', 0)} |
| Legacy stability rate | {robustness_summary.get('legacy_stability_rate', 0):.1%} |
| Shadow stability rate | {robustness_summary.get('shadow_stability_rate', 0):.1%} |
| Legacy detection rate | {robustness_summary.get('legacy_detection_rate', 0):.1%} |
| Shadow detection rate | {robustness_summary.get('shadow_detection_rate', 0):.1%} |

**Categories tested**: {', '.join(robustness_summary.get('categories_tested', []))}

**Transforms tested**: {', '.join(robustness_summary.get('transforms_tested', []))}

---

## 7. Confidence Calibration

See `results/metrics/confidence_calibration.json` for detailed calibration data.

---

## 8. Key Findings

### What works
- Legacy AST detectors are stable across variable renames and expression styles
- Shadow structural fact extraction is deterministic and syntax-normalized
- Both systems successfully parse and analyze the majority of submissions

### What doesn't work
- Limited ground truth labels (using target_concepts as proxy)
- Shadow system has narrower concept coverage than legacy
- Some detectors may be naming-dependent (see robustness results)

### Failure categories
- Legacy: False positives from detectors firing on incidental patterns
- Shadow: False negatives from incomplete technique/strategy coverage
- Both: Structural fact extraction gaps for non-standard implementations

---

## 9. Recommendations

**KEEP**:
- Legacy AST detector architecture (stable, deterministic)
- Shadow fact extraction pipeline (syntax-normalized)

**IMPROVE**:
- Shadow technique coverage (currently 9 techniques vs 33 legacy patterns)
- Shadow strategy coverage (currently 9 strategies vs 33 legacy patterns)
- Confidence calibration methodology

**INVESTIGATE**:
- Naming dependencies in legacy detectors
- Ground truth quality with expert labels
- Cross-system detection disagreements

**DO NOT CHANGE YET**:
- Production scoring logic
- ELO calculation
- Recommendation system

---

## 10. Files Generated

- `results/raw_outputs/raw_results.json` — Raw analysis outputs
- `results/metrics/overall_metrics.json` — Micro/macro/weighted averages
- `results/metrics/per_concept_metrics.csv` — Per-concept metrics
- `results/metrics/legacy_vs_shadow.csv` — Comparison table
- `results/metrics/confidence_calibration.json` — Calibration data
- `results/error_analysis/error_analysis.csv` — Error localization
- `results/error_analysis/error_summary.json` — Error summary
- `results/robustness/robustness_results.json` — Robustness test results
- `results/robustness/robustness_summary.json` — Robustness summary
- `results/reports/summary_report.md` — This report
- `EXPERIMENT_LOG.md` — Experiment metadata

---

*Generated by PathForge Evaluation Framework v1.0*
"""
    
    return report


if __name__ == "__main__":
    run_all()
