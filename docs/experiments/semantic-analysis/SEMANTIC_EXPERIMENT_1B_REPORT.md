# Semantic Experiment 1B: Scorer Calibration Report

## Summary

Built a 46-case calibration corpus and evaluated the semantic scorer's ability to discriminate between correct and incorrect patterns.

**Verdict: PARTIAL SUCCESS — two_pointers_opposite is well-calibrated, others need improvement before production use.**

---

## Corpus Description

| Pattern | Positive Cases | Negative Cases | Total |
|---------|---------------|----------------|-------|
| array_traversal | 9 | 7 | 16 |
| hash_map_lookup | 4 | 4 | 8 |
| prefix_sum | 5 | 3 | 8 |
| two_pointers_opposite | 3 | 3 | 6 |
| binary_search_* | 3 | 2 | 5 |
| other (untracked) | 3 | 0 | 3 |
| **Total** | **27** | **19** | **46** |

Sources: handwritten, LeetCode, adversarial variants.

---

## Per-Pattern Calibration

### array_traversal

**Score Distribution:**
- Positives: 0.00, 0.00, 0.25, 0.25, 0.25, 0.45, 0.80, 0.80, 0.80
- Negatives: 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.25

**Precision/Recall by Threshold:**

| Threshold | Precision | Recall | F1 | TP | FP | FN |
|-----------|-----------|--------|-----|----|----|-----|
| 0.3 | 1.00 | 0.44 | 0.62 | 4 | 0 | 5 |
| 0.5 | 1.00 | 0.33 | 0.50 | 3 | 0 | 6 |
| 0.7 | 1.00 | 0.33 | 0.50 | 3 | 0 | 6 |
| 0.9 | 0.00 | 0.00 | 0.00 | 0 | 0 | 9 |

**Analysis:**
- **Precision is excellent** (1.00 at all thresholds)
- **Recall is poor** (0.44 at best)
- **Root cause:** for-loop cases score 0.25 (below 0.3 threshold)
- The scorer doesn't recognize `for i in range(len(arr))` as a counter loop

**False Positives:** None

**False Negatives (5 cases):**
1. `array_traversal_for_loop` (0.25) — for-loop not recognized as counter
2. `array_traversal_enumerate` (0.25) — enumerate not recognized
3. `array_traversal_nested` (0.25) — nested for-loops
4. `adversarial_class_traversal` (0.00) — class method
5. `adversarial_list_comprehension` (0.00) — list comprehension

**Risk A Assessment:** `array_traversal = 1.00` is NOT over-rewarding. The maximum score in the corpus is 0.80, which is justified by 4 strong evidence signals (counter loop + indexed access + index movement + bound comparison). The score is well-calibrated for while-loop cases.

---

### hash_map_lookup

**Score Distribution:**
- Positives: 0.00, 0.20, 0.20, 0.35
- Negatives: 0.00, 0.00, 0.00, 0.35

**Precision/Recall by Threshold:**

| Threshold | Precision | Recall | F1 | TP | FP | FN |
|-----------|-----------|--------|-----|----|----|-----|
| 0.3 | 0.50 | 0.25 | 0.33 | 1 | 1 | 3 |
| 0.5 | 0.00 | 0.00 | 0.00 | 0 | 0 | 4 |
| 0.7 | 0.00 | 0.00 | 0.00 | 0 | 0 | 4 |
| 0.9 | 0.00 | 0.00 | 0.00 | 0 | 0 | 4 |

**Analysis:**
- **Poor calibration** across all thresholds
- **Root cause:** The scorer doesn't detect dict/set creation, so it can't distinguish hash-based lookup from list membership
- **False positive:** Class method `item in self.data` scores 0.35

**False Positive:**
- `not_hashmap_class_method` (0.35) — membership in class method triggers score

**False Negatives (3 cases at threshold 0.3):**
1. `hashmap_two_sum` (0.20) — dict creation not detected
2. `hashmap_set_membership` (0.20) — set creation not detected
3. `hashmap_dict_lookup` (0.20) — dict lookup not detected

**Risk C Assessment:** `hash_map_lookup = 0.35` is a false positive. List membership is NOT appropriately distinguished from hash-based lookup because the scorer doesn't detect dict/set creation.

---

### prefix_sum

**Score Distribution:**
- Positives: 0.10, 0.10, 0.30, 0.70, 0.85
- Negatives: 0.10, 0.30, 0.30

**Precision/Recall by Threshold:**

| Threshold | Precision | Recall | F1 | TP | FP | FN |
|-----------|-----------|--------|-----|----|----|-----|
| 0.3 | 0.60 | 0.60 | 0.60 | 3 | 2 | 2 |
| 0.5 | 1.00 | 0.40 | 0.57 | 2 | 0 | 3 |
| 0.7 | 1.00 | 0.40 | 0.57 | 2 | 0 | 3 |
| 0.9 | 0.00 | 0.00 | 0.00 | 0 | 0 | 5 |

**Analysis:**
- **Moderate calibration** at threshold 0.3
- **False positives** at low thresholds: simple counter (0.30) and string concat (0.30)
- **Root cause:** The scorer treats any `+=` as accumulation, doesn't distinguish numeric from string

**False Positives (2 cases at threshold 0.3):**
1. `not_prefixsum_simple_accumulator` (0.30) — counter increment, not prefix sum
2. `not_prefixsum_string_concat` (0.30) — string concatenation, not numeric

**False Negatives (2 cases at threshold 0.3):**
1. `prefixsum_running_total` (0.30) — just barely passes
2. `prefixsum_cumulative` (0.10) — different accumulation pattern

**Risk B Assessment:** `prefix_sum = 0.85` is legitimate (while-loop with accumulation from collection). However, simple accumulators CAN be mistaken for prefix-sum at lower thresholds (0.30).

---

### two_pointers_opposite

**Score Distribution:**
- Positives: 0.50, 0.50, 0.50
- Negatives: 0.00, 0.00, 0.00

**Precision/Recall by Threshold:**

| Threshold | Precision | Recall | F1 | TP | FP | FN |
|-----------|-----------|--------|-----|----|----|-----|
| 0.3 | 1.00 | 1.00 | 1.00 | 3 | 0 | 0 |
| 0.5 | 1.00 | 1.00 | 1.00 | 3 | 0 | 0 |
| 0.7 | 0.00 | 0.00 | 0.00 | 0 | 0 | 3 |
| 0.9 | 0.00 | 0.00 | 0.00 | 0 | 0 | 3 |

**Analysis:**
- **Perfect calibration** at thresholds 0.3 and 0.5
- **Zero false positives** and **zero false negatives**
- **Risk D Assessment:** Bidirectional movement is sufficient evidence for this pattern. The 0.50 score is well-calibrated.

---

## Risk Investigation Summary

### Risk A: `array_traversal = 1.00`
**Verdict: NOT a problem.** Maximum corpus score is 0.80, justified by 4 strong evidence signals. The score correctly reflects while-loop traversal with indexed access.

### Risk B: `prefix_sum = 0.85`
**Verdict: MINOR ISSUE.** The 0.85 score is legitimate. However, simple accumulators score 0.30, which could cause false positives at low thresholds. Need to distinguish numeric accumulation from other types.

### Risk C: `hash_map_lookup = 0.35`
**Verdict: SIGNIFICANT ISSUE.** The scorer doesn't detect dict/set creation, so it can't distinguish hash-based lookup from list membership. This produces false positives and false negatives.

### Risk D: `two_pointers_opposite = 0.50`
**Verdict: NOT a problem.** Perfect calibration with zero false positives and zero false negatives.

---

## Recommended Scoring Rules

### Current Rules (with issues)

```python
# array_traversal: good, but misses for-loop cases
# hash_map_lookup: needs dict/set creation detection
# prefix_sum: needs numeric accumulation check
# two_pointers_opposite: good
```

### Recommended Improvements

1. **array_traversal:** Add for-loop recognition (range/enumerate/iteration)
2. **hash_map_lookup:** Add dict/set creation detection; penalize when collection is a list
3. **prefix_sum:** Add numeric type check; penalize string accumulation
4. **two_pointers_opposite:** No changes needed

---

## Recommended Thresholds

| Pattern | Recommended Threshold | Expected Precision | Expected Recall |
|---------|----------------------|-------------------|-----------------|
| array_traversal | 0.3 | 1.00 | 0.44 |
| hash_map_lookup | 0.3 | 0.50 | 0.25 |
| prefix_sum | 0.5 | 1.00 | 0.40 |
| two_pointers_opposite | 0.5 | 1.00 | 1.00 |

**Note:** These thresholds are conservative. Precision is prioritized over recall to avoid false positives.

---

## Is the Current Feature Set Sufficient?

**For two_pointers_opposite: YES** — bidirectional movement is sufficient.

**For array_traversal: PARTIALLY** — needs for-loop recognition.

**For hash_map_lookup: NO** — needs dict/set creation detection.

**For prefix_sum: PARTIALLY** — needs numeric type checking.

---

## Conclusion

The semantic scorer shows **promising discrimination** for two_pointers_opposite (perfect) and **moderate discrimination** for array_traversal and prefix_sum. However, hash_map_lookup needs significant improvement before production use.

**Before expanding to all 36 patterns, fix:**
1. For-loop recognition in array_traversal
2. Dict/set creation detection for hash_map_lookup
3. Numeric accumulation check for prefix_sum

**Do NOT proceed to all 36 patterns until these improvements are validated.**
