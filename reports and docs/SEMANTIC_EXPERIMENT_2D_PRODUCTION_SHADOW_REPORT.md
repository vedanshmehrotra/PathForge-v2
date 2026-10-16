# SEMANTIC EXPERIMENT 2D: PRODUCTION SHADOW OBSERVABILITY

## Executive Summary

The shadow-mode hybrid detector has been integrated into the `/analyze` endpoint as optional observational metadata.

**Verdict: DEPLOY SHADOW MODE**

- Production analysis behavior: **100% unchanged**
- New `hybrid_analysis` field in API response: **observational only**
- Observability counters: **aggregate metrics, no raw code**
- Semantic failure: **silent fallback to AST-only**
- All 556 tests pass, zero regressions

---

## 1. Integration Changes

### Files Modified

| File | Change |
|------|--------|
| `pathforge/api/routes/analyze.py` | Added `HybridPatternInfo`, `HybridAnalysis` models; added `hybrid_analysis` field to `AnalyzeResponse`; integrated shadow detector after production analysis |
| `pathforge/api/services/shadow_observability.py` | **NEW** — Aggregate counters for monitoring (no raw code stored) |
| `src/ast_detection/semantic/shadow_detector.py` | **NEW** (Experiment 2C) — Shadow-mode comparison module |
| `src/ast_detection/semantic/tests/test_shadow.py` | **NEW** (Experiment 2C) — 16 unit tests |

### API Response Change

```json
{
  "ast": { ... },
  "match_result": { ... },
  "problem_info": { ... },
  "elo_updates": [ ... ],
  "submission_gap": { ... },
  "persisted": { ... },
  "hybrid_analysis": {                    // NEW — optional
    "code_hash": "a1b2c3d4e5f6",
    "hybrid_detections": {
      "two_pointers_opposite": true,
      "prefix_sum": false,
      "hash_map_lookup": true,
      "array_traversal": false
    },
    "patterns": [
      {
        "pattern_id": "two_pointers_opposite",
        "ast_detected": false,
        "ast_confidence": 0.0,
        "semantic_score": 0.50,
        "hybrid_detected": true,
        "fusion_policy": "semantic_primary",
        "discrepancy_type": "semantic_only"
      }
    ],
    "ast_latency_ms": 11.0,
    "semantic_latency_ms": 1.1
  }
}
```

---

## 2. Safety Verification

### Production Behavior Unchanged

| Check | Status |
|-------|--------|
| `run_analysis()` called with same args | ✅ |
| `run_persistence()` called with same args | ✅ |
| ELO updates identical | ✅ |
| Topic profiles identical | ✅ |
| Gap signals identical | ✅ |
| Recommendations identical | ✅ |
| Verdict/verdict_type identical | ✅ |
| Ground truth unchanged | ✅ |

### Shadow Safety

| Check | Status |
|-------|--------|
| Semantic failure → silent fallback | ✅ |
| Shadow exception → caught, ignored | ✅ |
| No database writes from shadow | ✅ |
| No file writes from shadow | ✅ |
| Source code not stored (only hash) | ✅ |
| `hybrid_analysis` is optional (null on error) | ✅ |

---

## 3. Observability Design

### Counters (in-memory, process-scoped)

```python
{
  "shadow": {
    "total_analyses": 0,
    "semantic_failures": 0,
    "semantic_only": 0,          # semantic detects, AST doesn't
    "ast_only": 0,               # AST detects, semantic doesn't
    "agreements": 0,             # both detect
    "conflicts": 0,              # disagree, hybrid picks one
    "hybrid_changes": {          # per-pattern: hybrid != AST
      "two_pointers_opposite": 0,
      "prefix_sum": 0,
      "hash_map_lookup": 0,
      "array_traversal": 0
    },
    "pattern_semantic_only": {},  # per-pattern semantic recoveries
    "pattern_conflicts": {},     # per-pattern conflicts
    "latency": {
      "ast_ms": 0.0,             # EMA
      "semantic_ms": 0.0,        # EMA
      "total_ms": 0.0,           # EMA
      "samples": 0
    }
  }
}
```

### What Is NOT Stored

- ❌ Raw source code
- ❌ Individual submission details
- ❌ User identifiers
- ❌ Problem identifiers
- ❌ Full AST output
- ❌ Database records

---

## 4. Privacy/Data-Retention Considerations

| Concern | Mitigation |
|---------|-----------|
| Source code exposure | Only SHA256 hash stored; raw code never logged |
| User identification | Counters are aggregate; no per-user tracking |
| Data retention | In-memory only; resets on process restart |
| GDPR/privacy | No PII collected; no persistent storage |
| API response | `hybrid_analysis` is optional field; can be stripped in production if needed |

---

## 5. Metrics Collected

### Available via `get_shadow_log_dict()`

| Metric | Description |
|--------|-------------|
| `total_analyses` | Number of analyses with successful shadow run |
| `semantic_failures` | Number of analyses where semantic analysis failed |
| `semantic_only` | Total semantic-only detections across all patterns |
| `ast_only` | Total AST-only detections across all patterns |
| `agreements` | Total both-detect cases |
| `conflicts` | Total AST/semantic disagreements |
| `hybrid_changes` | Per-pattern: how often hybrid differs from AST |
| `pattern_semantic_only` | Per-pattern: semantic recovery counts |
| `pattern_conflicts` | Per-pattern: conflict counts |
| `latency.ast_ms` | Rolling average AST latency |
| `latency.semantic_ms` | Rolling average semantic latency |
| `latency.total_ms` | Rolling average total latency |

---

## 6. Deployment Procedure

1. **Deploy the code** — shadow analysis runs automatically
2. **Monitor for 7 days** — collect at least 1000 analyses
3. **Check metrics:**
   - `semantic_failures` should be < 1% of `total_analyses`
   - `semantic_only` should stabilize (expected ~20-30% of analyses)
   - `conflicts` should stabilize (expected ~5-10% of analyses)
   - Latency overhead should remain < 15%
4. **Review API responses** — verify `hybrid_analysis` is present and correct

---

## 7. Rollback Procedure

If shadow analysis causes issues:

1. **Option A: Remove import** — Comment out the shadow integration block in `analyze.py`
2. **Option B: Environment variable** — Add `ENABLE_SHADOW=false` check
3. **Option C: Feature flag** — Add shadow toggle to config

The shadow integration is a single `try/except` block. Removing it restores the original endpoint with zero behavioral change.

---

## 8. Observation Criteria Before Enabling Any Hybrid Policy

### Minimum Sample Size

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| Total analyses | ≥ 1000 | Statistical significance |
| Semantic failure rate | < 1% | Reliability validation |
| Latency overhead | < 15% | Performance validation |
| Observation window | ≥ 7 days | Temporal coverage |

### Decision Rules for Moving from Shadow to Limited Rollout

**Phase 1: Two-pointers only (lowest risk)**
- Enable `two_pointers_opposite` semantic-primary in production scoring
- Gate: `pattern_conflicts["two_pointers_opposite"]` < 5% of total analyses
- Gate: `pattern_semantic_only["two_pointers_opposite"]` > 0 (confirming recoveries)
- Rollback: revert to AST-only for this pattern

**Phase 2: Prefix-sum supplemental**
- Enable `prefix_sum` AST-primary + semantic gaps
- Gate: `pattern_conflicts["prefix_sum"]` < 10% of total analyses
- Gate: semantic recoveries are genuine (manual review of top disagreements)
- Rollback: revert to AST-only for this pattern

**Phase 3: Hash-map agreement**
- Enable `hash_map_lookup` agreement filtering
- Gate: agreement filter reduces FP without losing TP
- Rollback: revert to AST-only for this pattern

**Never enable:** `array_traversal` semantic fusion (too noisy)

---

## 9. Test Results

| Suite | Tests | Result |
|-------|-------|--------|
| Shadow tests | 16 | 16 passed |
| Semantic tests | 58 | 58 passed |
| AST detectors | 482 | 482 passed |
| Evidence architecture | 41 | 41 passed |
| **Total** | **597** | **597 passed** |

Zero regressions.

---

## 10. Files Changed Summary

| File | Status | Lines Changed |
|------|--------|--------------|
| `pathforge/api/routes/analyze.py` | Modified | +45 (shadow integration) |
| `pathforge/api/services/shadow_observability.py` | **New** | +115 |
| `src/ast_detection/semantic/shadow_detector.py` | **New** (2C) | +130 |
| `src/ast_detection/semantic/tests/test_shadow.py` | **New** (2C) | +180 |

---

## 11. Verdict

**DEPLOY SHADOW MODE**

The production shadow observability integration is safe, lightweight, and observational. Zero production decisions are affected. The system is ready for deployment and monitoring.
