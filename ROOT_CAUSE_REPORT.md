# Root-Cause Report: Manual Testing Findings

## Issue 1: Add Two Numbers — Wrong Ground Truth Pattern

### Observed Behavior
- User submitted a linked-list addition implementation
- AST detected: `two_pointers_same`
- Expected ground truth: `linked_list_reversal`
- Result: NO_MATCH
- Gap shown: `linked_list_reversal`

### Root Cause: LLM Generated Incorrect Ground Truth

**Evidence:**
1. The CSV file (`pathforge_problems_fixed.csv`) lists the correct pattern for problem 2 (Add Two Numbers) as `["two_pointers_same"]`
2. The ground truth used for matching comes from `problem_ground_truth.patterns`, which is populated by the LLM
3. The LLM (GPT-4o-mini via OpenRouter) incorrectly classified this problem as requiring `linked_list_reversal`
4. This is an LLM reasoning error — the problem involves traversing linked lists and adding digits, but the core pattern is two-pointer traversal, not reversal

**Classification:** Existing data problem (LLM ground truth quality)

**Code Locations:**
- `pathforge/llm/openrouter_client.py:_build_prompt()` — LLM prompt that generates patterns
- `pathforge/services/ground_truth_builder.py:build_ground_truth()` — stores LLM output
- `pathforge/db/problem_ground_truth` table — stores the incorrect pattern

**Why This Happened:**
The LLM prompt asks for algorithmic patterns and includes `linked_list_reversal` as a canonical pattern. For "Add Two Numbers," the LLM associated "linked list" with "reversal" rather than correctly identifying the traversal/addition pattern.

---

## Issue 2: Problem 2996 — Zero AST Detections

### Observed Behavior
- Code uses while loops to iterate through array and compute running sum
- AST detected: 0 patterns
- Expected ground truth: `hash_map_lookup`, `prefix_sum`
- Result: NO_MATCH
- Both expected patterns shown as missing gaps

### Root Cause: AST Detector Coverage Limitation (While-Loop Sensitivity)

**Evidence:**
1. The code uses `while i <= len(nums)-1 and nums[i] == nums[i-1]+1:` — a while loop
2. The `array_traversal` detector (`src/ast_detection/detectors/array_traversal.py`) only looks for `for` loops in `_detect_traversal_loop()`
3. No detector recognizes while-loop array traversal patterns
4. The `hash_map_lookup` detector doesn't trigger because `while summ in nums:` is a linear search, not a hash map operation
5. The `prefix_sum` detector doesn't trigger because the running sum pattern doesn't match its expected AST shape

**Which Detectors Should Theoretically Fire:**
| Detector | Why It Should Fire | Why It Doesn't |
|----------|-------------------|----------------|
| `array_traversal` | Iterates through array with index | Only detects `for` loops, not `while` loops |
| `hash_map_lookup` | Uses `in nums` for membership test | Linear search on list, not hash set |
| `prefix_sum` | Computes running sum | Running sum pattern doesn't match detector's expected shape |

**Classification:** Existing AST coverage problem (known loop-form sensitivity)

**Code Locations:**
- `src/ast_detection/detectors/array_traversal.py:_detect_traversal_loop()` — only checks `ast.For`, not `ast.While`
- `src/ast_detection/detectors/hash_map_lookup.py` — looks for `set()` or `dict()` usage, not `in list`
- `src/ast_detection/detectors/prefix_sum.py` — expects specific AST shape for prefix sums

**Note:** This is a known limitation from the Phase-0 adversarial evaluation. The evaluation identified that 17.8% of false negatives were caused by while-loop sensitivity.

---

## Evidence State and Verdict Type for Both Submissions

### Add Two Numbers (Problem 2)

| Property | Value | Source |
|----------|-------|--------|
| Evidence state | `llm_proposed` or `unobserved` | Depends on when ground truth was generated |
| verdict_type | `analysis_only` | Derived from evidence state |
| is_authoritative | `False` | Not in `_AUTHORITATIVE_STATES` |

### Problem 2996

| Property | Value | Source |
|----------|-------|--------|
| Evidence state | `llm_proposed` | Generated after evidence architecture |
| verdict_type | `analysis_only` | Derived from evidence state |
| is_authoritative | `False` | Not in `_AUTHORITATIVE_STATES` |

---

## Gap/ELO/Recommendation Gating Verification

### For Both Submissions (analysis_only verdict_type)

| System | Behavior | Correct? |
|--------|----------|----------|
| Gap signals (persisted) | SKIPPED — `_gap_engine.persist_signals()` not called | ✅ YES |
| Gap display (API response) | SHOWN — computed from `match_result["unmatched_patterns"]` | ✅ YES (informational) |
| user_pattern_elo | SKIPPED — entire block skipped | ✅ YES |
| topic_profiles | SKIPPED — `update_topic_profile()` not called | ✅ YES |
| recommendations | SKIPPED — `get_recommendation()` not called | ✅ YES |
| streak | UPDATED — always updated regardless of evidence | ✅ YES |

### Gating Is Correct

The evidence authority architecture is working as designed:
- Weak evidence (llm_proposed, unobserved) does NOT persist gap signals
- Weak evidence does NOT update ELO
- Weak evidence does NOT update topic profiles
- Weak evidence does NOT generate recommendations
- Gap information IS shown in the API response (informational only)

---

## Classification Summary

| Issue | Classification | Root Cause | Fix Required |
|-------|---------------|------------|--------------|
| Add Two Numbers wrong pattern | **Existing data problem** | LLM generated incorrect ground truth | Improve LLM prompt, add validation, or use CSV as fallback |
| Problem 2996 zero detections | **Existing AST coverage problem** | While-loop sensitivity (known limitation) | Add while-loop detection to `array_traversal` and other detectors |

---

## Recommended Next Steps

### For Ground Truth Quality (Add Two Numbers)
1. Add cross-validation between LLM-generated patterns and CSV patterns
2. When CSV pattern exists but LLM returns different pattern, prefer CSV pattern
3. Add manual review queue for problems where LLM and CSV disagree

### For AST Coverage (Problem 2996)
1. Add while-loop detection to `array_traversal` detector
2. Add linear search detection for `in list` patterns
3. Add running-sum detection for `summ += nums[i]` patterns
4. These are part of the Phase-2 AST improvement roadmap

### For Evidence Architecture
1. No changes needed — gating is working correctly
2. Consider adding a "confidence indicator" to the API response to show users when results are based on weak evidence
