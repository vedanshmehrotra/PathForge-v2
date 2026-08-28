# Experiment Log

**Date**: 2026-08-26

**Dataset Size**: 12 submissions (test run; full run targets 200)

**Concepts Evaluated**: 6 (test run; full vocabulary is 42)

**Legacy Success Rate**: 91.7%

**Shadow Success Rate**: 91.7%

## Known Limitations

- Ground truth uses `target_concepts` as proxy (no expert labels yet)
- Template solutions may not represent real coding diversity
- Only Python submissions tested
- Shadow system has limited concept coverage (9 techniques vs 33 legacy patterns)
- One submission failed to parse in both systems (likely invalid Python)

## Fixes Made

None - observational only. No production code was modified.

## Preliminary Observations (from test run)

- Legacy system detected 25 total patterns across 11 submissions
- Shadow system detected 12 total concepts across 11 submissions
- Legacy had higher recall (0.636 vs 0.455) but similar precision
- Robustness: Legacy 100% stable across variable renames; Shadow 64.3% stable
- Shadow stability issues: monotonic_stack variants, loop style changes

## Files Generated

- `results/raw_outputs/raw_results.json` — Raw analysis outputs
- `results/metrics/overall_metrics.json` — Micro/macro/weighted averages
- `results/metrics/per_concept_metrics.csv` — Per-concept metrics
- `results/metrics/legacy_vs_shadow.csv` — Comparison table
- `results/metrics/confidence_calibration.json` — Calibration data
- `results/error_analysis/error_analysis.csv` — Error localization
- `results/error_analysis/error_summary.json` — Error summary
- `results/robustness/robustness_results.json` — Robustness test results
- `results/robustness/robustness_summary.json` — Robustness summary

## To Run Full Evaluation

```bash
cd experiments/code_analysis_evaluation
python runners/run_all.py
```
