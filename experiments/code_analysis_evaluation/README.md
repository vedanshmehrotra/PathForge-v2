# PathForge Code Analysis Evaluation

A reproducible benchmark for evaluating PathForge's algorithmic concept detection systems.

## Purpose

This experiment measures how accurately PathForge's analysis pipeline detects algorithmic concepts and patterns from real programming submissions. It identifies where errors occur and produces a reproducible baseline for comparing against future improvements.

**This is observational only.** No production code is modified.

## Architecture

```
experiments/code_analysis_evaluation/
├── README.md                          # This file
├── EXPERIMENT_LOG.md                  # Experiment metadata
├── dataset/
│   ├── raw/                           # Raw submissions from CSV
│   ├── selected_submissions/          # Curated evaluation dataset
│   │   ├── submissions.json           # Full dataset
│   │   └── dataset_summary.json       # Dataset statistics
│   └── metadata/                      # Problem metadata
├── ground_truth/
│   ├── concept_vocabulary.json        # All detectable concepts
│   ├── labeling_guidelines.md         # What counts as evidence
│   ├── labels.json                    # Expert ground truth labels
│   └── uncertain_cases.json           # Ambiguous cases
├── runners/
│   ├── build_dataset.py               # Dataset construction
│   ├── run_evaluation.py              # Main evaluation runner
│   ├── calculate_metrics.py           # Metrics calculation
│   ├── error_analysis.py              # Error localization
│   ├── robustness_test.py             # Robustness testing
│   └── run_all.py                     # Orchestrator
├── results/
│   ├── raw_outputs/                   # Raw analysis outputs
│   │   ├── raw_results.json
│   │   └── evaluation_summary.json
│   ├── metrics/                       # Calculated metrics
│   │   ├── overall_metrics.json
│   │   ├── per_concept_metrics.csv
│   │   ├── legacy_vs_shadow.csv
│   │   └── confidence_calibration.json
│   ├── error_analysis/                # Error localization
│   │   ├── error_analysis.csv
│   │   └── error_summary.json
│   ├── robustness/                    # Robustness results
│   │   ├── robustness_results.json
│   │   └── robustness_summary.json
│   └── reports/                       # Generated reports
│       └── summary_report.md
```

## Quick Start

### 1. Run the complete evaluation

```bash
cd experiments/code_analysis_evaluation
python runners/run_all.py
```

### 2. Run individual steps

```bash
# Build dataset only
python runners/build_dataset.py

# Run analysis only
python runners/run_evaluation.py

# Calculate metrics only
python runners/calculate_metrics.py

# Error analysis only
python runners/error_analysis.py

# Robustness tests only
python runners/robustness_test.py
```

## What This Measures

### Systems Under Test

1. **Legacy (Production) System**
   - 33 AST-based pattern detectors
   - Matching Engine with LLM ground truth
   - Pattern-level detection

2. **Shadow (Experimental) System**
   - Structural fact extraction (25+ fact types)
   - 9 technique detectors
   - 9 strategy evaluators
   - Solution-group matching with authority gating

### Concepts Evaluated

The vocabulary includes 42 concepts across:
- Arrays & Hashing (hash_map_lookup, prefix_sum, sliding_window_*, two_pointers_*)
- Graphs & Trees (dfs_*, bfs_*, topological_sort, union_find)
- Dynamic Programming (dp_1d_*, dp_2d_*, dp_knapsack, dp_interval, dp_state_machine)
- Binary Search (binary_search_standard, binary_search_rotated, binary_search_answer)
- Heap/Greedy/Backtracking (heap_top_k, greedy_*, backtracking_*)
- Shadow-only techniques (sequential_accumulation, carry_propagation, recursive_branching, etc.)
- Shadow-only strategies (dp_top_down, dp_bottom_up, etc.)

### Metrics

- **Precision**: Fraction of detections that are correct
- **Recall**: Fraction of present concepts that were detected
- **F1**: Harmonic mean of precision and recall
- **False Positive Rate**: Fraction of absent concepts incorrectly detected
- **False Negative Rate**: Fraction of present concepts missed
- **Confidence Calibration**: Whether confidence scores correlate with correctness
- **Robustness**: Detection stability across variable renames, loop styles, etc.

### Error Localization

For every false positive/negative, classifies the failure as:
- `PARSER_FAILURE` — Code could not be parsed
- `STRUCTURAL_FACT_FAILURE` — Facts not extracted correctly
- `TECHNIQUE_DETECTION_FAILURE` — Techniques not detected despite facts
- `STRATEGY_INFERENCE_FAILURE` — Strategies not inferred despite techniques
- `SOLUTION_GROUP_MATCHING_FAILURE` — Matching produced wrong outcome
- `CONFIDENCE_FAILURE` — Detection present but confidence too low
- `GROUND_TRUTH_AMBIGUITY` — Ground truth label is uncertain
- `NAMING_DEPENDENCY` — Detection depends on variable names
- `FALSE_POSITIVE_SYSTEMATIC` — Detector fires on non-target patterns
- `MISSING_DETECTOR` — No detector exists for this concept
- `UNKNOWN` — Failure cause unclear

## Ground Truth

Ground truth labels should be created by:
1. Inspecting the actual submitted code
2. Identifying which algorithmic concepts are demonstrated
3. Marking ambiguous cases as `uncertain`
4. Using the labeling guidelines in `ground_truth/labeling_guidelines.md`

**Important**: Do NOT use PathForge's own detector output as ground truth.

## Limitations

- Uses `target_concepts` from templates as proxy ground truth (no expert labels yet)
- Template solutions may not represent real coding diversity
- Only Python submissions tested
- Shadow system has limited concept coverage (9 techniques vs 33 legacy patterns)

## Next Steps

1. Create expert ground truth labels for selected submissions
2. Expand dataset with real LeetCode submissions
3. Add more robustness test variants
4. Compare against research baselines (pattern-KC paper)
5. Use findings to guide architecture improvements

---

*Created as part of the PathForge evaluation framework. Do not modify production code.*
