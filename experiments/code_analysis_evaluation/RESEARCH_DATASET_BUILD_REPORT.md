# PathForge Research Dataset Build Report

## Date: August 27, 2026
## Specification: RESEARCH_DATASET_SPECIFICATION.md v2.0.0
## Status: **STOPPED BEFORE LABELING — BLOCKERS IDENTIFIED**

---

## 1. Executive Summary

The research dataset assembly was attempted but **STOPPED before labeling** due to two critical blockers:

1. **No two genuinely independent reviewers available** — The environment provides only an AI agent, not a human reviewer team. The specification requires two independent human reviewers plus a third for adjudication.

2. **Insufficient submissions** — 62 eligible submissions assembled vs. 388 minimum required.

**The dataset is NOT frozen. No labels have been applied. No detector tuning has occurred.**

---

## 2. What Was Assembled

### 2.1 Source Submissions

| Source | Count | Status |
|--------|:-----:|--------|
| Expanded evaluation hardcoded solutions | 81 | Mapped to v2 strategies |
| Old dataset (12 submissions) | 12 | **Excluded** — old corpus, not independently verified against v2 protocol |
| **Eligible submissions** | **62** | Mapped from 81 original (19 excluded as removed concepts) |
| **Excluded submissions** | **19** | Concepts removed from authoritative classification |

### 2.2 Per-Strategy Coverage

| Strategy | Assembled | Minimum Required | Deficit |
|----------|:---------:|:----------------:|:-------:|
| S01 binary_search | 7 | 20 | -13 |
| S02 sliding_window | 7 | 20 | -13 |
| S03 two_pointers_opposite | 5 | 15 | -10 |
| S04 dfs_backtracking | 11 | 15 | -4 |
| S05 dp_top_down | 2 | 15 | -13 |
| S06 dp_bottom_up | 10 | 15 | -5 |
| S07 bfs_shortest_path | 5 | 10 | -5 |
| S08 union_find | 2 | 10 | -8 |
| S09 monotonic_stack | 4 | 10 | -6 |
| S10 topological_sort | 1 | 8 | -7 |
| S11 linked_list_reversal | 2 | 10 | -8 |
| S12 fast_slow_pointers | 2 | 10 | -8 |
| S13 greedy_interval | 1 | 8 | -7 |
| S14 heap_selection | 1 | 8 | -7 |
| S15 dp_2d | 2 | 10 | -8 |
| **TOTAL** | **62** | **194** | **-132** |

### 2.3 Negative Examples

| Category | Assembled | Required |
|----------|:---------:|:--------:|
| confusable_strategy | 0 | 75 |
| structural_overlap | 0 | 45 |
| technique_only | 0 | 30 |
| unrelated | 0 | 105 |
| **TOTAL** | **0** | **194** |

### 2.4 Implementation Variants

| Variant Type | Count | Required per Strategy |
|-------------|:-----:|:---------------------:|
| standard | 46 | — |
| structural | 10 | — |
| recursive | 6 | — |
| renamed_vars | 0 | At least 3 of 5 types |
| loop_form | 0 | At least 3 of 5 types |
| control_flow | 0 | At least 3 of 5 types |
| style | 0 | At least 3 of 5 types |

### 2.5 Split Distribution

| Split | Submissions | Problems | Status |
|-------|:----------:|:--------:|--------|
| development | 0 | 0 | Not assigned |
| validation | 0 | 0 | Not assigned |
| test | 0 | 0 | Not assigned |
| unassigned | 62 | ~35 | Awaiting split assignment |

---

## 3. Blockers

### BLOCKER 1: No Independent Reviewers (CRITICAL)

**Specification Requirement** (Section 8.1):
> Number of reviewers: 2 independent reviewers per submission

**Specification Requirement** (Section 10.4):
> If the environment does not provide two genuinely independent reviewers, STOP before labeling and report the blocker.

**What Happened**: The environment provides a single AI agent (Buffy/Codebuff). This agent cannot serve as two independent reviewers — it has a single perspective and cannot simulate independent human judgment.

**Impact**: No labels can be applied. No inter-rater agreement can be computed. No dataset can be frozen.

**Required to Resolve**:
- Two human reviewers with 50+ LeetCode problems solved each
- 10-hour calibration exercise for each reviewer
- Third reviewer for adjudication
- Labeling interface/tool for independent first-pass labeling

### BLOCKER 2: Insufficient Submissions (CRITICAL)

**Specification Requirement** (Section 3.1):
> Total positive submissions: minimum 194

**What We Have**: 62 eligible submissions

**Deficit**: 132 submissions (68% shortfall)

**What's Missing**:
- Real Python submissions for each of the 15 strategies
- Submissions from at least 95 distinct problems
- Submissions spanning Easy/Medium/Hard difficulty levels
- Submissions with diverse implementation styles

**Required to Resolve**:
- Collect real Python submissions from LeetCode public discussions
- Each submission must be a complete function body
- Each must be non-AI-generated, non-editorial, non-paid-archive
- Source provenance must be tracked

### BLOCKER 3: No Negative Examples (CRITICAL)

**Specification Requirement** (Section 3.1):
> Total negative/cross-pattern submissions: minimum 194

**What We Have**: 0 negative examples

**Deficit**: 194 submissions

**What's Missing**:
- Submissions where the target strategy is NOT the primary approach
- Submissions with confusable strategies
- Submissions with structural overlap but different intent
- Submissions using techniques without the target strategy

---

## 4. Excluded Submissions

### 4.1 Old Corpus (12 submissions)

**Reason**: The old dataset (`dataset/selected_submissions/submissions.json`) was created under the v1 evaluation protocol, not the v2 research protocol. Per specification requirement #6: "Do NOT use the old 300-question PathForge corpus as the research dataset unless individual submissions independently satisfy the new v2 protocol."

**Status**: Excluded. Would need independent verification against v2 criteria before inclusion.

### 4.2 Removed Concepts (19 submissions)

**Reason**: These submissions were labeled with concepts removed from authoritative classification in the Research Taxonomy Review:
- hash_map_lookup (4 submissions)
- hash_map_frequency (4 submissions)
- prefix_sum (2 submissions)
- greedy_local (2 submissions)
- two_pointers_same (3 submissions)
- array_traversal (counted within other concepts)
- brute_force (counted within other concepts)

**Status**: Excluded from strategy-level dataset. Could be repurposed as negative examples if they genuinely represent different strategies.

---

## 5. Schema Compliance

### 5.1 Schema Structure Created

The following directory structure was created:
```
experiments/code_analysis_evaluation/dataset/research_v2/
├── development/          (empty — awaiting split assignment)
├── validation/           (empty — awaiting split assignment)
├── test/                 (empty — awaiting split assignment)
└── labeling_workflow/    (empty — awaiting reviewer setup)
```

### 5.2 Schema Fields Populated

For the 62 assembled submissions, the following fields are populated:
- `problem_id` ✅ (mapped from concept)
- `submission_id` ✅
- `source` ✅ (marked as 'expanded_evaluation_historical')
- `language` ✅ (python3)
- `code` ❌ (not available in raw results)
- `correctness` ✅ (from original evaluation)
- `primary_strategy` ✅ (mapped from legacy concept)
- `secondary_strategies` ✅ (empty — needs reviewer input)
- `secondary_techniques` ✅ (empty — needs reviewer input)
- `ambiguity_flag` ✅ (default false — needs reviewer input)
- `evidence` ✅ (placeholder — needs reviewer input)
- `implementation_variant` ✅ (mapped from legacy style)
- `problem_split` ❌ (unassigned — needs split assignment)
- `reviewer labels` ❌ (no reviewers available)
- `final adjudicated label` ❌ (no reviewers available)

### 5.3 Critical Missing Fields

- **`code`**: The actual Python source code is not stored in the expanded evaluation raw results. The hardcoded solutions exist in `expanded_evaluation.py` but are not extracted into the schema.
- **`reviewer_a`**: No reviewer available
- **`reviewer_b`**: No reviewer available
- **`third_reviewer`**: No reviewer available
- **`final_label`**: Cannot be computed without reviewers

---

## 6. Leakage Checks

### 6.1 Cross-Split Problem Leakage

**Status**: NOT CHECKED — splits not yet assigned.

### 6.2 Duplicate Code

**Status**: NOT CHECKED — code not yet extracted into schema.

### 6.3 AI-Generated Code

**Status**: The 62 assembled submissions are from the expanded evaluation hardcoded solutions, which are hand-written LeetCode solutions (not AI-generated). However, provenance documentation is incomplete.

---

## 7. Provenance Summary

| Source | Count | Provenance Verified | Notes |
|--------|:-----:|:-------------------:|-------|
| expanded_evaluation.py hardcoded | 62 | Partial | Solutions appear to be hand-written LeetCode solutions |
| Old dataset submissions.json | 12 | No | Excluded per v2 protocol |
| pathforge_problems_fixed.csv | 0 (metadata only) | N/A | Problem metadata, not submissions |

---

## 8. What's Required to Proceed

### Immediate (Before Any Labeling)

1. **Recruit two human reviewers** with 50+ LeetCode problems solved each
2. **Conduct calibration exercise** (10 hours per reviewer)
3. **Collect ~400 real Python submissions** from LeetCode public discussions
4. **Extract actual code** into the schema (currently missing)
5. **Assign problem-disjoint splits**
6. **Collect ~200 negative examples** across all strategies

### Before Dataset Freeze

7. **Complete dual-labeling** of all submissions
8. **Adjudicate all disagreements** with third reviewer
9. **Compute inter-rater agreement** metrics
10. **Verify all minimum requirements** from Section 3
11. **Compute freeze hash** (SHA-256)
12. **Commit to version control**

---

## 9. Remaining Deficits

| Requirement | Current | Minimum | Deficit |
|------------|:-------:|:-------:|:-------:|
| Positive submissions | 62 | 194 | -132 |
| Negative submissions | 0 | 194 | -194 |
| Distinct problems | ~35 | 95 | -60 |
| Implementation variants | 3 types | 55 total | -52 |
| Independent reviewers | 0 | 2 | -2 |
| Adjudicator | 0 | 1 | -1 |
| Labeled submissions | 0 | 388 | -388 |
| Frozen test set | No | Yes | Not started |

---

## 10. Labeling Status

**NOT STARTED.** No labels have been applied. No reviewer has reviewed any submission. The dataset is in pre-labeling state only.

---

## 11. Verdict

**THE DATASET CANNOT BE BUILT OR FROZEN IN THIS ENVIRONMENT.**

Three critical blockers prevent completion:
1. No human reviewers available
2. Insufficient submissions (62 vs 388)
3. No negative examples (0 vs 194)

**Next steps must be taken by the project owner**:
1. Recruit human reviewers
2. Collect real submissions from LeetCode
3. Set up labeling infrastructure
4. Execute the v2 protocol with human reviewers

The specification, audit, and schema are ready. The dataset assembly infrastructure is prepared. But the actual data collection and labeling requires human effort that cannot be automated.
