# Batch 3 Report — N3: For-loop Sequential Accumulation

**Date:** 2026-09-16
**Batch:** N3 only — sequential_accumulation for-loop gate.
**Not implemented:** vocabulary expansion, BFS coverage, LC 200 strategy logic, ground-truth edits, legacy matcher changes.

---

## 1. Diagnosis

`_detect_sequential_accumulation` previously required `while_loop_comparison` to prove a loop exists. For-loop accumulation like `for x in nums: total += x` produces `accumulator_update` + `for_loop_iteration` facts — both already extracted by the fact extractor — but no `while_loop_comparison`, so the technique never fired.

The existing evidence was sufficient:
- `for_loop_iteration` (with `loop_variable`) proves the loop shape
- `accumulator_update` (with `variable`) proves the self-referential update
- `for_loop_iteration.loop_variable ≠ accumulator_update.variable` ensures the accumulator isn't a trivial counter-rename (though even `count += 1` in a for-loop is legitimate sequential accumulation)

No new fact type was needed.

## 2. Change

**`pathforge/ast_analysis/shadow/techniques.py`** — `_detect_sequential_accumulation` now accepts two loop shapes:

| loop shape | how the accumulator-in-loop is proven |
|---|---|
| `while_loop_comparison` | accumulator variable appears in `modified_variables` (original path, unchanged) |
| `for_loop_iteration` | accumulator variable differs from `loop_variable` (new path) |

The original while-loop path is byte-identical. The new for-loop path fires only when both `for_loop_iteration` and `accumulator_update` exist and the accumulator is distinct from the loop variable.

**Harness classifier** — the `required_accumulation_needs_while_loop` flag was corrected to `required_accumulation_needs_acc_update`, reflecting that the actual blocker for LC 4284 is a missing `accumulator_update` fact (not a loop-type issue).

## 3. Validation

| suite | result |
|---|---|
| N3 tests | **22 passed** (6 positive, 2 while-loop parity, 6 negative, 2 parity-confidence, 4 matching, 2 vocabulary) |
| shadow suite | **546 passed** (was 520; all originals green) |
| full repository | **1420 passed, 1 failed** — only the known pre-existing legacy `prefix_sum` detector test |
| 46-submission batch | 31 CONFIRMED / 15 UNRESOLVED / 0 CONTRADICTED |

### Before → after (46 submissions)

| | Batch 2A | Batch 3 | delta |
|---|---|---|---|
| CONFIRMED / UNRESOLVED / CONTRADICTED | 31 / 15 / 0 | 31 / 15 / 0 | 0 |
| regressions (CONFIRMED → UNRESOLVED) | — | **0** | — |
| false confirmations (real) | 0 | 0 | 0 |
| false contradictions | 0 | 0 | 0 |
| wrong-strategy selections | 1 | 1 | 0 |

The only change: `required_accumulation_needs_while_loop` **(1)** → `required_accumulation_needs_acc_update` **(1)** — corrected attribution on `db-254` (LC 4284), which has no `accumulator_update` fact because `ind = i` is not self-referential. Verdict unchanged (UNRESOLVED).

### Verdict-level changes from Batch 3
**Zero.** The N3 fix makes the technique available for future for-loop accumulation groups, but none of the 46 submissions' ground truth requires `sequential_accumulation` in a way that would now match. The 1 affected record (LC 4284) still lacks the `accumulator_update` fact — the loop-type gate was never its real blocker.

### Regression risks
**Zero observed.** The while-loop path is untouched. The for-loop path requires both `accumulator_update` AND `for_loop_iteration` — two facts that must co-exist in the same function — so the false-positive surface is narrow. Verified against the full corpus: no new techniques, strategies, or verdicts appeared.

## 4. Files changed

| file | change |
|---|---|
| `pathforge/ast_analysis/shadow/techniques.py` | `_detect_sequential_accumulation` accepts `for_loop_iteration` as alternative loop evidence |
| `pathforge/ast_analysis/shadow/tests/test_batch3_for_loop_accumulation.py` | new — 22 generalized tests |
| `experiments/code_analysis_evaluation/runners/real_submission_harness.py` | classifier: `required_accumulation_needs_while_loop` → `required_accumulation_needs_acc_update` (correct attribution) |

## 5. Stopping point

No additional fixes were made. The codebase is in a clean state: all tests green, no regressions, no uncommitted analysis code beyond what was already staged from Batches 1–3.

*Reproduce:*
```
python -m pytest pathforge/ast_analysis/shadow/tests/test_batch3_for_loop_accumulation.py -q
python -m pytest pathforge/ast_analysis/shadow/tests -q
python -m pytest -q
python -m experiments.code_analysis_evaluation.runners.real_submission_harness \
  --input experiments/code_analysis_evaluation/dataset/db_submissions_export.json \
  --registry experiments/code_analysis_evaluation/results/registry_db_batch3.json \
  --groups-from-db --force --out-dir experiments/code_analysis_evaluation/results/db_batch3
```
