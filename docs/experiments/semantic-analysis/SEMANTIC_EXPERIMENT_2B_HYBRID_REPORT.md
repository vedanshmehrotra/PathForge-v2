# SEMANTIC EXPERIMENT 2B: HYBRID DETECTOR ARCHITECTURE

## Executive Summary

Five fusion policies were evaluated per pattern across 1160 cases. The analysis reveals that AST and semantic evidence are largely **complementary** — semantic recovers cases AST misses, while AST rarely misses cases semantic catches.

**Verdict: PATTERN-SPECIFIC FUSION APPROVED**

| Pattern | Recommended Policy | F1 | vs AST-only Δ | Precision safe? |
|---------|-------------------|-----|---------------|----------------|
| two_pointers_opposite | **Semantic-primary** | 0.905 | +0.072 | ✅ (P=0.935) |
| prefix_sum | **AST-primary + semantic gaps** | 0.800 | +0.008 | ⚠️ (P=0.686) |
| hash_map_lookup | **Agreement** | 0.921 | +0.007 | ✅ (P=0.914) |
| array_traversal | **AST-only** | 0.416 | — | ❌ (P=0.284) |

**Critical finding:** The AST detector itself has 106 false positives on the full corpus for `array_traversal` (all from cross-pattern code). This is NOT a semantic scorer problem — the AST detector is also too broad when applied outside its own test cases.

---

## 1. Corpus

- 1160 cases total: 48 seeds, 174 adversarial variants, 888 cross-pattern negatives
- Both AST engine and semantic scorer run on every case
- Per-case data: `ast_detected`, `ast_confidence`, `sem_score`, `sem_detected`

---

## 2. Fusion Policies Tested

### Policy A: AST-only
```
detect = ast_detected
```
Baseline. No semantic involvement.

### Policy B: Semantic-only
```
detect = sem_detected  (score >= threshold)
```
No AST involvement.

### Policy C: AST-primary (semantic fills gaps)
```
detect = ast_detected OR (sem_detected AND ast_confidence == 0)
```
Semantic only fires when AST is completely silent.

### Policy D: Agreement
```
detect = ast_detected AND sem_detected
```
Both must agree for high confidence.

### Policy E: Pattern-specific (recommended)
Custom policy per pattern based on empirical evidence.

---

## 3. Per-Pattern Metrics

### two_pointers_opposite

| Policy | TP | FP | TN | FN | P | R | F1 |
|--------|----|----|----|----|----|----|-----|
| AST-only | 35 | 0 | 229 | 14 | 1.000 | 0.714 | 0.833 |
| Semantic-only | 43 | 3 | 226 | 6 | 0.935 | 0.878 | 0.905 |
| AST-primary | 43 | 3 | 226 | 6 | 0.935 | 0.878 | 0.905 |
| Agreement | 35 | 0 | 229 | 14 | 1.000 | 0.714 | 0.833 |
| **Semantic-primary** | **43** | **3** | **226** | **6** | **0.935** | **0.878** | **0.905** |

**Best: Semantic-primary** — F1 +0.072 over AST-only. Only 3 FPs (all cross-pattern sliding window/binary search). 8 AST misses recovered.

### prefix_sum

| Policy | TP | FP | TN | FN | P | R | F1 |
|--------|----|----|----|----|----|----|-----|
| AST-only | 40 | 11 | 220 | 10 | 0.784 | 0.800 | 0.792 |
| Semantic-only | 48 | 14 | 217 | 2 | 0.774 | 0.960 | 0.857 |
| **AST-primary + gaps** | **48** | **22** | **209** | **2** | **0.686** | **0.960** | **0.800** |
| Agreement | 40 | 3 | 228 | 10 | 0.930 | 0.800 | 0.860 |
| AST-or-semantic-high | 45 | 20 | 211 | 5 | 0.692 | 0.900 | 0.783 |

**Best for recall: AST-primary + gaps** — recovers 8 AST misses (F1=0.800).
**Best for precision: Agreement** — P=0.930, F1=0.860 (no recall improvement).
**Tradeoff:** AST-primary + gaps costs 11 precision points for 16 recall points.

### hash_map_lookup

| Policy | TP | FP | TN | FN | P | R | F1 |
|--------|----|----|----|----|----|----|-----|
| AST-only | 64 | 7 | 235 | 5 | 0.901 | 0.928 | 0.914 |
| Semantic-only | 66 | 30 | 212 | 3 | 0.688 | 0.957 | 0.800 |
| AST-primary | 66 | 31 | 211 | 3 | 0.680 | 0.957 | 0.795 |
| **Agreement** | **64** | **6** | **236** | **5** | **0.914** | **0.928** | **0.921** |
| Semantic-high-only | 21 | 12 | 230 | 48 | 0.636 | 0.304 | 0.412 |

**Best: Agreement** — F1 +0.007 over AST-only. Actually improves precision (FP: 7→6) while maintaining recall. Semantic-only has 30 FPs which makes it unusable as primary.

### array_traversal

| Policy | TP | FP | TN | FN | P | R | F1 |
|--------|----|----|----|----|----|----|-----|
| **AST-only** | **42** | **106** | **130** | **12** | **0.284** | **0.778** | **0.416** |
| Semantic-only | 36 | 112 | 124 | 18 | 0.243 | 0.667 | 0.356 |
| AST-primary | 54 | 134 | 102 | 0 | 0.287 | 1.000 | 0.446 |
| Agreement | 24 | 84 | 152 | 30 | 0.222 | 0.444 | 0.296 |
| AST+very-high-sem | 54 | 109 | 127 | 0 | 0.331 | 1.000 | 0.498 |

**Verdict: BOTH DETECTORS FAIL on cross-pattern code.** The AST detector has 106 FPs (all from sorting, brute force, DFS, BFS code that happens to traverse arrays). Semantic has 112 FPs. Neither is usable as a standalone pattern classifier at this scale.

---

## 4. Evidence Complementarity Analysis

### Agreement Quadrant (per pattern)

| Pattern | Both detect | AST-only | Semantic-only | Both miss |
|---------|------------|----------|--------------|-----------|
| array_traversal | 24 | 18 | 12 | 0 |
| hash_map_lookup | 64 | 0 | 2 | 3 |
| prefix_sum | 40 | 0 | 8 | 2 |
| two_pointers_opposite | 35 | 0 | 8 | 6 |

### False Positive Quadrant

| Pattern | Both fire | AST-only FP | Semantic-only FP |
|---------|----------|-------------|-----------------|
| array_traversal | 84 | 22 | 28 |
| hash_map_lookup | 6 | 1 | 24 |
| prefix_sum | 3 | 8 | 11 |
| two_pointers_opposite | 0 | 0 | 3 |

### Key Insights

1. **Semantic recovers AST misses:** For hash_map_lookup (2), prefix_sum (8), and two_pointers_opposite (8), semantic catches cases AST misses. Total: 18 recovered.

2. **AST rarely misses semantic catches:** For hash_map_lookup (0), prefix_sum (0), and two_pointers_opposite (0), AST catches nothing that semantic misses. The detectors are complementary, not redundant.

3. **False positive overlap varies:**
   - array_traversal: 84/106 AST FPs also fire semantic → mostly shared failures
   - hash_map_lookup: 6/7 AST FPs also fire semantic → mostly shared failures
   - prefix_sum: 3/11 AST FPs also fire semantic → semantic adds 11 new FPs
   - two_pointers_opposite: 0/0 AST FPs → semantic adds only 3 new FPs

---

## 5. Pattern-Specific Recommendations

### two_pointers_opposite: SEMANTIC-PRIMARY

```
detect = sem_detected OR ast_detected
```

**Rationale:**
- Semantic F1 (0.905) exceeds AST F1 (0.833)
- Only 3 new FPs introduced (sliding window, binary search)
- 8 AST misses recovered (expression variants)
- Precision remains high (0.935)

**Risk:** 3 FPs are cross-pattern code. Acceptable for a supplementary signal.

### prefix_sum: AST-PRIMARY + SEMANTIC GAPS

```
detect = ast_detected OR (sem_detected AND ast_confidence == 0)
```

**Rationale:**
- Semantic recovers 8 AST misses (append/assignment accumulation)
- AST precision is higher than semantic (0.784 vs 0.774)
- When AST is silent, semantic provides valuable signal
- Precision drops from 0.784 to 0.686 — significant but recoverable

**Risk:** 22 total FPs (11 from AST, 11 from semantic). The 11 new semantic FPs are generic accumulation in cross-pattern code.

**Alternative:** Use Agreement policy (P=0.930, F1=0.860) if precision is critical.

### hash_map_lookup: AGREEMENT

```
detect = ast_detected AND sem_detected
```

**Rationale:**
- Agreement actually IMPROVES precision (FP: 7→6) by filtering 1 AST FP
- Maintains identical recall (R=0.928)
- Semantic-only has 30 FPs — too many to use as primary
- AST-primary adds semantic FPs without meaningful recall gain

**Risk:** None. Agreement is strictly better than AST-only.

### array_traversal: AST-ONLY (no semantic fusion)

```
detect = ast_detected
```

**Rationale:**
- Both detectors have catastrophic FP rates on cross-pattern code
- AST has 106 FPs, semantic has 112 FPs
- Fusion cannot fix a fundamental concept-breadth problem
- The semantic concept "iterates a collection" is indistinguishable from sorting, brute force, DFS, etc.

**Root cause:** `array_traversal` as defined in the AST taxonomy mixes:
- Primary array traversal strategy (correct usage)
- Incidental collection iteration in other algorithms (cross-pattern)

**Recommendation:** Do NOT fuse. Either keep AST-only or redefine the pattern.

---

## 6. Recommended Hybrid Policy

```python
FUSION_POLICIES = {
    "two_pointers_opposite": "semantic_primary",
    "prefix_sum": "ast_primary_semantic_gaps",
    "hash_map_lookup": "agreement",
    "array_traversal": "ast_only",
}

def detect_pattern(pattern, ast_result, sem_result):
    if pattern == "two_pointers_opposite":
        return sem_result["detected"] or ast_result["detected"]
    
    elif pattern == "prefix_sum":
        ast_det = ast_result["detected"]
        sem_det = sem_result["detected"]
        ast_conf = ast_result["confidence"]
        return ast_det or (sem_det and ast_conf == 0)
    
    elif pattern == "hash_map_lookup":
        return ast_result["detected"] and sem_result["detected"]
    
    elif pattern == "array_traversal":
        return ast_result["detected"]
```

---

## 7. Expected Impact

| Pattern | Current AST F1 | Hybrid F1 | Δ | New FPs | Recovered FNs |
|---------|---------------|-----------|---|---------|--------------|
| two_pointers_opposite | 0.833 | 0.905 | +0.072 | +3 | +8 |
| prefix_sum | 0.792 | 0.800 | +0.008 | +11 | +8 |
| hash_map_lookup | 0.914 | 0.921 | +0.007 | -1 | 0 |
| array_traversal | 0.416 | 0.416 | 0.000 | 0 | 0 |

**Net improvement:** +16 recovered FNs, +13 new FPs, +0.087 aggregate F1.

---

## 8. What Must Remain Semantic-Only/Provisional

1. **Semantic scores should NOT directly affect ELO or scoring** until validated in production shadow mode.

2. **Semantic-only detections for two_pointers_opposite** should be marked as `analysis_only` (not authoritative) until the 3 FPs are investigated.

3. **Semantic gaps for prefix_sum** should carry reduced confidence until the 11 new FPs are validated.

4. **array_traversal semantic evidence** should NOT be used for any decision until the concept is refined.

---

## 9. What This Experiment Proves

1. **AST and semantic evidence are complementary** — they catch different failure modes.

2. **Pattern-specific fusion is necessary** — no single global rule works for all patterns.

3. **Semantic evidence can safely improve two_pointers_opposite** with minimal precision cost.

4. **Semantic evidence can supplement prefix_sum** but introduces precision risk.

5. **Semantic evidence cannot improve array_traversal** — the concept is too broad.

6. **Agreement filtering improves hash_map_lookup** — semantic helps filter AST false positives.

7. **The AST detector itself has cross-pattern FP issues** — this is NOT just a semantic problem.

---

## 10. Test Results

| Suite | Tests | Result |
|-------|-------|--------|
| Semantic tests | 58 | 58 passed |
| AST detectors | 482 | 482 passed |
| **Total** | **540** | **540 passed** |

Zero regressions. No production code was modified.

---

## 11. Next Experiment

**Experiment 2C: Shadow Mode Validation**

Before integrating the hybrid policy into production:
1. Run the hybrid detector alongside existing production analysis
2. Log discrepancies between hybrid and current results
3. Verify that the 13 new FPs don't affect user scoring
4. Validate that the 16 recovered FNs represent genuine improvements
5. Measure latency impact of running both engines
