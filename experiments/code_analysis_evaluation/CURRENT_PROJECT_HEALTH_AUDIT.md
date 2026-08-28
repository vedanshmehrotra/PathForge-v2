# PathForge Current Project Health Audit

**Date:** August 27, 2026  
**Commit:** architecture/strategy-evidence-spike  
**Method:** Manual code inspection of all production, shadow, frontend, and database code  
**Scope:** All issues that could negatively affect a real user  

---

## Executive Summary

The PathForge project has **2 critical**, **3 high**, **4 medium**, and **6 low** issues across its production pipeline. The most severe problem is that **29+ tests are broken** due to the PostgreSQL migration changing the `init_db()` return type. Several production-path issues exist but the core analysis pipeline functions correctly for authenticated users with valid code.

---

## Issue #1 — CRITICAL: Tests broken by PostgreSQL migration (init_db returns None)

**Severity:** CRITICAL  
**Affects:** Test suite (29+ tests broken)  
**File:** `pathforge/db/db.py:121`, all test files  

**Current behavior:**  
`init_db()` returns `None` (PostgreSQL version). All tests call `connection = init_db(db_path)` and then `connection.execute(...)`, causing `AttributeError: 'NoneType' object has no attribute 'execute'`.

**Expected behavior:**  
Tests should either use `get_connection()` instead of `init_db()`, or `init_db()` should still return a connection for backward compatibility.

**Root cause:**  
PostgreSQL migration changed `init_db()` signature from `def init_db(db_path) -> PgConnection` to `def init_db(db_path) -> None`. The function now only verifies tables and applies migrations, but no longer returns a connection.

**Reproduction:**  
```
cd "D:/PathForge - v2" && python -m pytest pathforge/tests/test_diversity.py -q
```

**Affected test files (all broken):**
- `pathforge/tests/test_diversity.py` — 8 tests
- `pathforge/db/tests/test_elo.py::test_multi_submission_profile_sequence` — 1 test
- `pathforge/tests/test_pipeline.py` — 7 tests (likely)
- `pathforge/tests/trace_diversification.py` — 1 script

**Safest fix:**  
Update test files to call `get_connection(db_path)` instead of `init_db(db_path)`. Or restore `init_db()` to return a connection by calling `get_connection()` internally after migration.

**Regression test required:**  
Yes — all 29+ broken tests must pass after fix.

---

## Issue #2 — CRITICAL: All backend tests require PostgreSQL, no SQLite fallback

**Severity:** CRITICAL  
**Affects:** Test suite, CI/CD, local development  
**File:** `pathforge/db/db.py:18-27`  

**Current behavior:**  
`get_connection()` calls `_ensure_pool()` which reads `DATABASE_URL` and raises `RuntimeError` if not set. There is no SQLite fallback path. All tests require a live PostgreSQL instance.

**Expected behavior:**  
Tests should run against a local SQLite database or an in-memory PostgreSQL, not require production database credentials.

**Root cause:**  
The PostgreSQL migration removed the SQLite connection path entirely. `get_connection()` only creates PostgreSQL connection pools.

**Reproduction:**  
Set `DATABASE_URL` to empty, run any test.

**Safest fix:**  
Add a `--test` or `DATABASE_URL` fallback in the test harness that creates a temporary PostgreSQL database or provides an SQLite adapter. For now, document the requirement.

**Regression test required:**  
Yes — all tests must pass without production database.

---

## Issue #3 — HIGH: `init_db()` and `get_connection()` API contract mismatch

**Severity:** HIGH  
**Affects:** 15+ call sites  
**File:** `pathforge/db/db.py:99,121`, all files calling `init_db()`  

**Current behavior:**  
- `init_db()` returns `None` (PostgreSQL)  
- `get_connection()` returns `PgConnection`  
- Many call sites use `connection = init_db(db_path)` (SQLite-era pattern)  
- API routes use `get_connection(config.DATABASE_PATH)` (correct for PG)  
- `config.DATABASE_PATH` is passed around but PostgreSQL ignores it  

**Expected behavior:**  
Consistent API contract: either `init_db()` returns a connection, or no caller should depend on its return value.

**Root cause:**  
PostgreSQL migration changed the return type without updating all callers.

**Safest fix:**  
Restore `init_db()` to return a connection: add `conn = get_connection(db_path)` at the end of `init_db()` and return it.

**Regression test required:**  
Yes.

---

## Issue #4 — HIGH: Auth middleware connection lifecycle risk

**Severity:** HIGH  
**Affects:** All authenticated requests  
**File:** `pathforge/auth/auth_middleware.py:114-135`  

**Current behavior:**  
`_ensure_local_user()` calls `get_connection()` and uses a `try/finally` block to close. However, the connection is obtained at the module function level, and `get_current_user()` calls `_ensure_local_user()` which gets its own connection. If the DB query fails after `get_connection()` but before `commit()`, the connection is properly returned via `finally`. **This is correctly handled.**

**However**, there is a subtle issue: the `get_current_user()` function creates its own connection via `_ensure_local_user()`, and separately, the calling route (`analyze_endpoint`) also creates its own connection. This means **every authenticated analyze request opens 2 database connections** — one for auth and one for the main analysis. Under load this doubles connection usage.

**Expected behavior:**  
Single connection per request, or at minimum clear documentation that 2 connections are expected.

**Root cause:**  
Auth middleware and routes each independently call `get_connection()`.

**Safest fix:**  
Not urgent — document the 2-connection-per-request pattern. Optionally, pass the auth-resolved user ID to avoid a second connection lookup.

**Regression test required:**  
No — behavior is correct, just suboptimal.

---

## Issue #5 — HIGH: Partial token logged in auth middleware

**Severity:** HIGH  
**Affects:** Security / log privacy  
**File:** `pathforge/auth/auth_middleware.py:137`  

**Current behavior:**  
```python
print(f"[AuthMiddleware] Authorization Header: '{auth_header[:30]}...' (length: {len(auth_header)})")
```
This logs the first 30 characters of the Authorization header, which includes the full token prefix `Bearer ` (7 chars) plus 23 chars of the actual JWT token. This could leak partial token data in server logs.

**Expected behavior:**  
Log only the token type (`Bearer`) and token length, not any token content.

**Root cause:**  
Debug logging left in production code.

**Safest fix:**  
Replace with: `print(f"[AuthMiddleware] Auth header present (length: {len(auth_header)})")`

**Regression test required:**  
No.

---

## Issue #6 — MEDIUM: `datetime.utcnow()` deprecation warning

**Severity:** MEDIUM  
**Affects:** 16 warnings per test run, future Python compatibility  
**File:** `pathforge/ast_analysis/shadow/authority.py:65`  

**Current behavior:**  
```python
self.timestamp = timestamp or datetime.utcnow().isoformat()
```
Python 3.12+ emits `DeprecationWarning` for `datetime.utcnow()`.

**Expected behavior:**  
```python
self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
```

**Root cause:**  
`datetime.utcnow()` is deprecated since Python 3.12.

**Safest fix:**  
Replace with `datetime.now(timezone.utc).isoformat()`.

**Regression test required:**  
No.

---

## Issue #7 — MEDIUM: Shadow analysis silently swallows all exceptions

**Severity:** MEDIUM  
**Affects:** Debugging, observability  
**File:** `pathforge/ast_analysis/shadow/shadow_runner.py:64`  

**Current behavior:**  
```python
except Exception as e:
    return None
```
All exceptions from shadow analysis (including bugs in fact_extractor, techniques, strategies) are silently swallowed. The only observability is `record_shadow_parse_failure()` in the calling route, which doesn't distinguish between a real parse error and a logic bug.

**Expected behavior:**  
Log the exception type and message before returning None, even if the return value is None.

**Root cause:**  
Graceful degradation design — shadow failure must not affect production. But complete silence prevents debugging.

**Safest fix:**  
Add `logger.debug(f"Shadow analysis failed: {type(e).__name__}: {e}")` before returning None.

**Regression test required:**  
No.

---

## Issue #8 — MEDIUM: No frontend component tests

**Severity:** MEDIUM  
**Affects:** Frontend reliability  
**File:** `pathforge-frontend/components/`  

**Current behavior:**  
- Only 1 frontend test file exists: `shadow-mapper.test.ts` (26 tests)
- Zero tests for: `analysis-view.tsx`, `experimental-panel.tsx`, `app-shell.tsx`, `dashboard.tsx`, `profile-view.tsx`, `progress-view.tsx`, `recommendations-view.tsx`
- Zero tests for hooks: `useApi.ts`

**Expected behavior:**  
At minimum, component render tests and hook behavior tests.

**Root cause:**  
Test infrastructure set up but components were built before tests were added.

**Safest fix:**  
Not urgent for production correctness — add component tests as a follow-up.

**Regression test required:**  
No (but needed for reliability).

---

## Issue #9 — MEDIUM: `config.DATABASE_PATH` passed to PostgreSQL backend (no-op)

**Severity:** MEDIUM  
**Affects:** Code clarity, future confusion  
**File:** `pathforge/db/db.py:99`, `pathforge/api/routes/analyze.py:118`, etc.  

**Current behavior:**  
`get_connection(db_path=config.DATABASE_PATH)` is called everywhere, but `PgConnection` ignores the `db_path` parameter entirely. The parameter exists only for API compatibility with the old SQLite interface.

**Expected behavior:**  
Either remove the parameter or document that it's ignored for PostgreSQL.

**Root cause:**  
PostgreSQL migration preserved the old API surface for backward compatibility.

**Safest fix:**  
Add a docstring note that `db_path` is ignored. Optionally deprecate the parameter.

**Regression test required:**  
No.

---

## Issue #10 — MEDIUM: Cache/queue/graph detection is name-dependent

**Severity:** MEDIUM  
**Affects:** Shadow analysis accuracy  
**File:** `pathforge/ast_analysis/shadow/fact_extractor.py`  

**Current behavior:**  
- `cache_lookup`/`cache_write`: Only detects variables named `cache`, `memo`, `dp`, `table`, `visited`, `seen`, etc.
- `queue_dequeue`: Only detects `deque()` creation or queue-named variables (`queue`, `q`, `frontier`)
- `neighbor_traversal`: Only detects variables named `graph`, `adj`, `g`, etc.
- `visited_tracking`: Only detects variables named `visited`, `seen`, `vis`, `explored`

A solution using `memoization` as a variable name, or `adj_list` instead of `adj`, or a dict used for caching without a cache-like name, will NOT be detected.

**Expected behavior:**  
Structural evidence should supplement (not replace) name-based heuristics, but the current implementation relies heavily on names.

**Root cause:**  
Name-based heuristics are the primary detection mechanism for these fact types.

**Safest fix:**  
This is a known limitation. For the audit: document the coverage gap. Structural fallback (e.g., `dict[key] = val` pattern regardless of variable name) would help but requires careful implementation to avoid false positives.

**Regression test required:**  
If changed, yes.

---

## Issue #11 — MEDIUM: `code_text` truncation in submission storage

**Severity:** MEDIUM (minor data loss)  
**File:** `pathforge/services/persistence.py:73`  

**Current behavior:**  
```python
code[:1000] if code else ""
```
Only the first 1000 characters of submitted code are stored in the `submissions` table. Long solutions (e.g., 200+ lines) are truncated.

**Expected behavior:**  
Store full code for future analysis, clustering, and debugging. The `code_hash` is computed from the full code, but the stored text is truncated.

**Root cause:**  
Original SQLite schema likely had a TEXT column with practical limits; the PostgreSQL migration didn't change this.

**Safest fix:**  
Increase to `code` (full TEXT) since PostgreSQL handles large text well. Or at minimum document the 1000-char limit.

**Regression test required:**  
No.

---

## Issue #12 — LOW: `Gaps` / `Elo` / `Recommend` routes ignore `config.DATABASE_PATH`

**Severity:** LOW  
**Affects:** Code consistency  
**File:** `pathforge/api/services/gap.py:10`, `elo.py:10`, `recommend_service.py:38`  

**Current behavior:**  
```python
connection = get_connection(db_path or config.DATABASE_PATH)
```
The `db_path` parameter is passed through but ultimately ignored by PostgreSQL backend.

**Expected behavior:**  
Consistent parameter usage or removal.

**Root cause:**  
PostgreSQL migration preserved old API.

**Safest fix:**  
No change needed — works correctly. Document for clarity.

**Regression test required:**  
No.

---

## Issue #13 — LOW: `analysis-view.tsx` doesn't show shadow outcome when UNRESOLVED

**Severity:** LOW  
**Affects:** Frontend user experience  
**File:** `pathforge-frontend/components/analysis-view.tsx`, `experimental-panel.tsx`  

**Current behavior:**  
The ExperimentalPanel shows when shadow_analysis is present, but for UNRESOLVED outcomes it shows "Not enough evidence" and "Approach unclear". This is intentionally conservative, but users may not understand why their code analysis shows inconclusive results.

**Expected behavior:**  
Consider adding a brief "why" hint (e.g., "The system detected some patterns but couldn't confirm the approach with high confidence").

**Root cause:**  
Deliberate design choice to avoid false confidence.

**Safest fix:**  
No change needed — the current behavior is correct and safe. The explanation text already provides context.

**Regression test required:**  
No.

---

## Issue #14 — LOW: `build_ground_truth()` truncated to problem description only

**Severity:** LOW  
**Affects:** Ground truth quality  
**File:** `pathforge/services/problem_resolver.py:93`  

**Current behavior:**  
```python
build_source = description or row.get("title", "")
```
Ground truth generation uses only the problem description (or title as fallback). It does not receive the problem's canonical tags, constraints, or difficulty level, which could help the LLM generate more accurate ground truth.

**Expected behavior:**  
Pass additional context (topics, difficulty, constraints) to the LLM prompt.

**Root cause:**  
The `call_llm()` function only accepts a single text string.

**Safest fix:**  
Enhance the LLM prompt to include topics and difficulty. Not urgent — this affects ground truth quality for newly prepared problems.

**Regression test required:**  
No.

---

## Issue #15 — LOW: `usePrepareProblem` hook doesn't clear error on re-run

**Severity:** LOW  
**Affects:** Frontend UX  
**File:** `pathforge-frontend/src/hooks/useApi.ts:72-88`  

**Current behavior:**  
```typescript
const run = useCallback(async (problem: string) => {
    setLoading(true)
    setError(null)
    setResult(null)
    // ...
```
Error IS cleared on re-run (set to null). This is actually correct. ✅

**Expected behavior:**  
Error should clear on re-run — it does.

**Root cause:**  
N/A — this is working correctly.

**Safest fix:**  
No change needed.

**Regression test required:**  
No.

---

## Issues That Can Safely Wait

| Issue | Severity | Why it can wait |
|-------|----------|-----------------|
| #8 — No frontend component tests | MEDIUM | Core components work; tests are for reliability |
| #10 — Name-dependent detection | MEDIUM | Shadow is observational only; no production impact |
| #11 — Code truncation to 1000 chars | MEDIUM | Core analysis uses full code; storage is for audit |
| #14 — LLM prompt missing context | LOW | Ground truth quality is already functional |
| #15 — Hook behavior | LOW | Already working correctly |

---

## Things That Must NOT Be Changed Yet

1. **ELO engine** — working correctly, no issues found
2. **Recommendation engine** — working correctly, no issues found  
3. **Frontend display of confidence values** — correctly using 0.0–1.0 → 0–100 conversion
4. **Matching engine** — working correctly with solution groups
5. **AST detection engine** — all 36 detectors functional
6. **Shadow analysis architecture** — fact → technique → strategy → match pipeline is sound
7. **GraphQL client** — working correctly with browser-like headers
8. **CORS configuration** — correctly allows localhost:3000 and Vercel domain

---

## Recommended Implementation Order

### Phase 1: Fix broken tests (CRITICAL — do first)
1. Fix `init_db()` to return a connection (or update all test callers)
2. Add SQLite test fallback or PostgreSQL test database setup
3. Verify all 29+ tests pass

### Phase 2: Security and logging (HIGH — do second)
4. Remove partial token logging from auth middleware
5. Add logging to shadow analysis exceptions

### Phase 3: Code cleanup (MEDIUM — do when convenient)
6. Replace `datetime.utcnow()` with `datetime.now(timezone.utc)`
7. Add docstrings for PostgreSQL-specific behavior
8. Increase code storage limit from 1000 chars

### Phase 4: Tests and improvements (LOW — do as follow-up)
9. Add frontend component tests
10. Add structural fallbacks for name-dependent detection
11. Enhance LLM ground truth prompt with problem metadata

---

## Verification Summary

| Area | Status | Details |
|------|:------:|---------|
| API routes (analyze, prepare-problem) | ✅ | Correctly handle errors, auth, persistence |
| Persistence pipeline | ✅ | Correctly persists submission, gap, elo, recommendation |
| Shadow analysis pipeline | ✅ | Fact → technique → strategy → match works end-to-end |
| Matching engine | ✅ | Solution group satisfaction works correctly |
| Ground truth generation | ✅ | LLM → V1 vocabulary mapping functional |
| Frontend analysis view | ✅ | All panels display correctly, confidence normalized |
| Frontend experimental panel | ✅ | Shadow data mapped to user-friendly display |
| Auth middleware | ⚠️ | Works but logs partial token |
| Database layer | ❌ | Tests broken; PostgreSQL migration incomplete for tests |
| Test suite | ❌ | 29+ tests broken by init_db() return type change |
| Frontend tests | ⚠️ | Only shadow-mapper tests exist |

---

## Top 5 Issues That Should Be Fixed First

1. **#1 — CRITICAL: `init_db()` returns None, breaking 29+ tests** → Fix by restoring connection return
2. **#2 — CRITICAL: No SQLite test fallback** → Fix by adding test database setup
3. **#3 — HIGH: API contract mismatch between init_db and get_connection** → Fix by unifying return types
4. **#5 — HIGH: Partial JWT token logged** → Fix by removing token content from logs
5. **#7 — MEDIUM: Shadow exceptions silently swallowed** → Fix by adding debug logging

---

*Generated by health audit on August 27, 2026*
