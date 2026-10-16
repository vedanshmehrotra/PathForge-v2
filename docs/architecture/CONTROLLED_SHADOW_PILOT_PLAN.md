# Controlled Shadow Pilot Plan

## Purpose

Validate real-world behavior of the shadow analysis architecture (fact extraction → technique detection → strategy evaluation → solution-group matching) on real user submissions. The 883-case disjoint evaluation has passed the architecture safety gate with 0 spurious CONFIRMED results, 342/342 negative cases correctly UNRESOLVED, precision 1.000, recall 0.569, and 892 tests passing.

This pilot is **strictly observational**. No production scoring, verdicts, ELO updates, topic profiles, gap signals, or recommendations are affected.

---

## 1. Pilot Duration

| Phase | Duration | Purpose |
|-------|----------|---------|
| **Phase 1: Observation** | 4 weeks minimum | Collect shadow results from real user submissions |
| **Phase 2: Analysis** | 2 weeks | Analyze collected metrics, audit confirmed cases |
| **Phase 3: Decision** | 1 week | Go/no-go decision on next phase |

**Total minimum duration: 7 weeks** before any production activation consideration.

Phase 1 may be extended if sample size targets are not met.

---

## 2. Minimum Sample Size

| Metric | Minimum Required | Rationale |
|--------|-----------------|-----------|
| **Total shadow analyses** | 500 | Statistical significance for rate estimation |
| **CONFIRMED cases** | 50 | Sufficient to audit plausibility |
| **UNRESOLVED cases** | 200 | Sufficient to categorize failure modes |
| **Unique strategies observed** | ≥ 3 | Ensure coverage beyond two-pointers |
| **Unique problems observed** | ≥ 20 | Ensure coverage across problem types |
| **Observation window** | 4 weeks minimum | Capture weekly usage patterns |

The pilot does not end until both the sample size AND the minimum duration are satisfied.

---

## 3. Metrics

### 3.1 Primary Metrics

| Metric | Definition | Target |
|--------|-----------|--------|
| **Shadow CONFIRMED rate** | `confirmed / total_analyses` | Report only (no target) |
| **Shadow UNRESOLVED rate** | `unresolved / total_analyses` | Report only (no target) |
| **Shadow CONTRADICTED rate** | `contradictions / total_analyses` | Must be 0 |
| **Extractor failure rate** | `failures / total_analyses` | < 5% |
| **Precision of CONFIRMED cases** | `plausible_confirmed / audited_confirmed` | ≥ 0.95 |

### 3.2 Strategy Breakdown Metrics

| Metric | Definition |
|--------|-----------|
| **Confirmations by strategy** | Count of CONFIRMED outcomes per strategy_id |
| **Unresolved by strategy** | Count of UNRESOLVED outcomes per strategy_id |
| **Strategy extraction rate** | `submissions_with_strategy / total_analyses` |
| **Technique extraction rate** | `submissions_with_technique / total_analyses` |

### 3.3 Latency Metrics

| Metric | Definition | Target |
|--------|-----------|--------|
| **p50 latency** | Median shadow analysis time | < 50ms |
| **p95 latency** | 95th percentile shadow analysis time | < 200ms |
| **p99 latency** | 99th percentile shadow analysis time | < 500ms |
| **Max latency** | Maximum observed shadow analysis time | < 1000ms |

### 3.4 Pipeline Health Metrics

| Metric | Definition | Target |
|--------|-----------|--------|
| **AST parse failures** | Submissions where `ast.parse()` fails | < 2% |
| **Fact extraction rate** | `submissions_with_facts / total_analyses` | > 90% |
| **Technique detection rate** | `submissions_with_techniques / total_analyses` | > 40% |
| **Strategy detection rate** | `submissions_with_strategies / total_analyses` | > 20% |

---

## 4. Success Criteria

The pilot is considered **successful** if ALL of the following hold:

| # | Criterion | Threshold |
|---|-----------|-----------|
| 1 | **Zero spurious CONFIRMED** | 0 CONFIRMED cases that are factually wrong after audit |
| 2 | **Precision ≥ 0.95** | ≥ 95% of audited CONFIRMED cases are plausible |
| 3 | **No production impact** | Zero changes to production verdict, ELO, topics, gaps, recommendations |
| 4 | **Extractor reliability** | < 5% extractor/parse failures |
| 5 | **Latency acceptable** | p95 < 200ms |
| 6 | **Sample size met** | ≥ 500 analyses, ≥ 50 CONFIRMED, ≥ 200 UNRESOLVED |
| 7 | **No contradictions** | 0 authoritative CONTRADICTED outcomes |
| 8 | **Graceful degradation** | Shadow failures never affect production response |

---

## 5. Rollback Conditions

The pilot is **immediately rolled back** if ANY of the following occur:

| # | Condition | Action |
|---|-----------|--------|
| 1 | **Production impact detected** | Disable shadow analysis entirely |
| 2 | **Latency regression** | p95 > 500ms for > 1 hour sustained |
| 3 | **Error rate spike** | Extractor failure rate > 20% for > 30 minutes |
| 4 | **Memory pressure** | Shadow observability counters cause OOM |
| 5 | **Database impact** | Shadow persistence queries slow down production writes |
| 6 | **Spurious CONFIRMED** | Any CONFIRMED case confirmed wrong during real-time audit |

**Rollback mechanism:** Comment out the shadow analysis call in `analyze.py` (2 lines). No data loss — all shadow results are stored in existing submission columns.

---

## 6. How Confirmed Cases Will Be Sampled for Correctness

### 6.1 Sampling Strategy

- **Random sample:** 20% of all CONFIRMED cases are flagged for manual audit
- **Stratified by strategy:** Ensure each strategy's confirmed cases are represented
- **Stratified by authority tier:** Sample across `llm_proposed`, `structurally_observed`, `bootstrap`
- **All CONTRADICTED cases:** 100% manual audit (if any occur)

### 6.2 Audit Process

1. Retrieve the submission's `code_hash` from the shadow metadata
2. Retrieve the original `code_text` from the submissions table (for authorized auditors only)
3. Verify the claimed technique/strategy is actually present in the code
4. Verify the solution group satisfaction is correct
5. Record audit result: `correct`, `incorrect`, `ambiguous`

### 6.3 Privacy Safeguards

- `code_hash` is a SHA-256 one-way hash — cannot be reversed to source code
- Raw code is stored in `submissions.code_text` (existing column, access-controlled)
- Audit access requires admin role
- No PII is logged in shadow observability counters
- Shadow metadata contains only: hash, strategy ID, group ID, satisfaction score, authority state, versions, latency

---

## 7. How Unresolved Cases Will Be Categorized

### 7.1 Categories

| Category | Definition | Expected Cause |
|----------|-----------|----------------|
| **No solution groups** | `groups` is None or empty | Problem not prepared yet |
| **No technique match** | Techniques detected but don't satisfy any group's requirements | Extractor vocabulary gap |
| **No strategy match** | Strategies detected but don't satisfy any group's requirements | Strategy definition gap |
| **Below threshold** | Satisfaction score below group threshold | Confidence calibration issue |
| **Excluded evidence** | Excluded technique/strategy detected | Over-aggressive exclusion rules |
| **Parse failure** | AST parsing failed | Code has syntax errors or unsupported Python |
| **Empty extraction** | No facts extracted | Extractor coverage gap |

### 7.2 Categorization Process

For each UNRESOLVED case, record:
- Which category it falls into
- The specific technique/strategy IDs that were detected (if any)
- The specific group IDs that were evaluated
- The satisfaction score achieved vs. the threshold required

### 7.3 Priority for Vocabulary Expansion

Categories are prioritized for future extractor/technique work:
1. **No technique match** (highest) — indicates vocabulary gap
2. **Below threshold** — indicates confidence calibration issue
3. **Excluded evidence** — indicates over-aggressive exclusion
4. **No strategy match** — indicates strategy definition gap
5. **No solution groups** — not actionable (problem preparation issue)
6. **Parse failure** — not actionable (user code issue)
7. **Empty extraction** (lowest) — rare, may be irreducible

---

## 8. Evidence Required Before Production Activation

Before ANY production activation of the shadow architecture, ALL of the following must be demonstrated:

### 8.1 Pilot Completion

- [ ] Pilot duration ≥ 7 weeks completed
- [ ] Sample size targets met (500+ analyses, 50+ CONFIRMED, 200+ UNRESOLVED)
- [ ] All success criteria met (Section 4)

### 8.2 Correctness Evidence

- [ ] ≥ 95% precision on audited CONFIRMED cases
- [ ] Zero spurious CONFIRMED cases
- [ ] Zero authoritative CONTRADICTED outcomes
- [ ] Confirmed cases span ≥ 3 different strategies
- [ ] Confirmed cases span ≥ 20 different problems

### 8.3 Performance Evidence

- [ ] p95 latency < 200ms sustained over 4 weeks
- [ ] No memory growth trend (counter leak check)
- [ ] No database query performance regression
- [ ] Extractor failure rate < 5%

### 8.4 Safety Evidence

- [ ] Zero production impact incidents during pilot
- [ ] Rollback mechanism tested (comment out 2 lines → shadow disabled)
- [ ] Shadow persistence does not slow down production writes
- [ ] All shadow data is observational only (no scoring, no ELO, no recommendations)

### 8.5 Vocabulary Readiness

- [ ] Top 5 unresolved categories identified and addressed
- [ ] Technique vocabulary expanded to cover ≥ 80% of observed code patterns
- [ ] Strategy vocabulary expanded to cover ≥ 80% of observed algorithmic patterns
- [ ] Solution group definitions validated against real ground truth

### 8.6 Documentation

- [ ] Shadow-to-production promotion runbook written
- [ ] Rollback procedure documented and tested
- [ ] Monitoring dashboards configured
- [ ] Alerting thresholds defined

---

## Appendix A: Observational Metadata Schema

For every shadow CONFIRMED result, the following metadata is recorded:

```json
{
  "code_hash": "sha256hexdigest",
  "strategy_id": "two_pointers_opposite",
  "satisfied_group_ids": ["g0"],
  "satisfaction_score": 0.9,
  "authority_tier": "llm_proposed",
  "extractor_version": "1.0.0",
  "technique_def_version": "1.0.0",
  "strategy_def_version": "1.0.0",
  "elapsed_ms": 12.5,
  "techniques_detected": ["bidirectional_index_scan"],
  "strategies_detected": ["two_pointers_opposite"]
}
```

## Appendix B: Aggregate Counter Schema

```json
{
  "shadow_pipeline": {
    "total_analyses": 0,
    "confirmed": 0,
    "unresolved": 0,
    "contradictions": 0,
    "parse_failures": 0,
    "extraction_failures": 0,
    "confirmed_by_strategy": {},
    "unresolved_by_strategy": {},
    "unresolved_by_category": {},
    "technique_extraction_rate": 0.0,
    "strategy_extraction_rate": 0.0,
    "latency": {
      "p50_ms": 0.0,
      "p95_ms": 0.0,
      "p99_ms": 0.0,
      "max_ms": 0.0,
      "samples": 0
    }
  }
}
```

## Appendix C: Production Guardrails

| Layer | Guardrail | Implementation |
|-------|-----------|----------------|
| **Code** | Shadow analysis wrapped in try/except | `analyze.py` lines ~170-185 |
| **Code** | Shadow results returned in response only | Never used for scoring decisions |
| **Code** | Shadow persistence separate from production | `shadow/persistence.py` updates shadow columns only |
| **Data** | Shadow columns are nullable | Schema uses `ADD COLUMN IF NOT EXISTS` |
| **Runtime** | Shadow counters are in-memory only | Reset on process restart |
| **Monitoring** | Shadow metrics logged separately | Structured logging with `shadow_pipeline` prefix |
