# PathForge — AGENTS.md

## Goal
- Implement problem-aware analysis for PathForge where `POST /analyze` loads ground truth from DB only, and `POST /prepare-problem` does the slow cache-building (GraphQL + LLM).

## Constraints & Preferences
- Do NOT rewrite existing engines (AST Detection, Matching Engine, Gap, Elo, Recommendation).
- ProblemResolver is the ONLY module allowed to call GraphQL or invoke ground truth generation.
- GraphQL and OpenRouter are cache builders only, never called during runtime analysis.
- Ground truth generation happens exactly once per problem, never auto-regenerated.
- When preparation fails (GraphQL down, OpenRouter down), return HTTP 502 with error message; do not cache empty results.
- Confidence values in the backend are on a 0.0–1.0 scale; frontend must multiply by 100 for display.
- Frontend threshold comparisons must use the normalized 0–1 value, not the displayed percentage.

## Progress
### Done
- Created `pathforge/llm/graphql_client.py` — `fetch_problem_by_slug`, `fetch_title_slug_by_id`, `html_to_plain_text`, `GraphQLUnavailableError`. Added browser-like HTTP headers (User-Agent, Accept, Referer, Origin) to fix 403 Forbidden from LeetCode.
- Added `pattern NOT NULL` fix in `problem_resolver.py:_fetch_and_store_problem()` — `'[]'` default value for new problems.
- Added migration `_ensure_problem_metadata_columns()` in `db.py` — creates `title_slug` + `description` columns and backfills from `link`.
- Created `pathforge/services/problem_resolver.py` — `resolve_problem()` orchestrates DB lookup, GraphQL cache-fill, ground truth generation, returns `ProblemContext`.
- Created `pathforge/api/routes/prepare_problem.py` — `POST /prepare-problem` endpoint.
- Created `pathforge/api/routes/analyze.py` — updated with structured `ProblemIdentifier` model (`leetcode_id?`, `title_slug?`).
- Modified `pathforge/api/services/analysis.py` — `run_analysis()` accepts `accepted_solution_groups` parameter, no longer builds synthetic groups.
- Registered `prepare_problem_router` in `pathforge/api/app.py`.
- Added error handling: `GraphQLUnavailableError` + `GroundTruthError` caught in both route handlers → HTTP 502. `ValueError` remains 404.
- Added `GroundTruthError` in `ground_truth_builder.py` — raised when LLM returns None instead of caching empty `[], {}`.
- Updated frontend `api.ts` with `PrepareRequest`, `PrepareResponse`, structured `problem` field in `AnalyzeRequest`.
- Added `prepareProblem()` in `endpoints.ts`.
- Added `usePrepareProblem()` hook in `useApi.ts`.
- Updated `analysis-view.tsx` with problem input row, prepare button, prepared state display (title + difficulty badge), structured problem sent to `/analyze`.
- Fixed frontend matching engine display: changed keys from `overall_match` → `confidence_score`, `matched_patterns` → `matched_groups`, `divergent_patterns` → `unmatched_patterns`.
- Fixed frontend confidence scale (0.0–1.0 → 0–100): added shared `pct()` helper, fixed Meter values, badge threshold, and percentage text across AST and Matching Engine panels. Badge threshold compares raw `>= 0.8`.
- Verified all backend/frontend compilation (Python + TypeScript zero errors).
- Created `pathforge/services/persistence.py` — `run_persistence()` persists analysis results: submission row with actual AST data, gap signals (GapSignalEngine), Elo updates (EloEngine), topic profile (update_topic_profile), streak (_update_user_streak), and recommendation (get_recommendation + _log_recommendation). Does NOT call GraphQL or LLM.
- Modified `pathforge/api/routes/analyze.py` — calls `run_persistence()` after successful analysis, wraps in try/except with atomic commit/rollback, returns `persisted` info in `AnalyzeResponse`. Changed `user_id` from `str` to `int`.
- Modified `pathforge/api/routes/prepare_problem.py` — enhanced error messages with user-friendly guidance.
- Updated frontend `api.ts` — `AnalyzeRequest.user_id` changed from `string` to `number`.
- Updated `analysis-view.tsx` — `handleRun` passes numeric `user_id`, updated placeholder text.
- Verified all backend/frontend compilation (Python + TypeScript zero errors).
- **PostgreSQL Migration (Batch 1-3)**: Added `psycopg2-binary` to requirements.txt. Created `pathforge/db/schema_pg.sql` with PostgreSQL syntax (SERIAL, LEAST, no AUTOINCREMENT, no PRAGMA). Rewrote `pathforge/db/db.py` to use psycopg2 connection pool with `PgConnection` wrapper mimicking sqlite3.Row dict access. Updated all SQL queries across 13 files: `?` → `%s`, `INSERT OR REPLACE` → `ON CONFLICT DO UPDATE`, `INSERT OR IGNORE` → `ON CONFLICT DO NOTHING`, `cursor.lastrowid` → `RETURNING id`, `json_extract()` → `->>` JSON operators, `MIN()` → `LEAST()`. Verified Python compilation (zero errors).

### In Progress
- PostgreSQL Migration: Batch 1-3 complete. Remaining: seed data migration from SQLite → Supabase, Render env var configuration.

### Blocked
- None.

## Key Decisions
- `ProblemIdentifier` uses two optional fields (`leetcode_id?`, `title_slug?`) instead of a plain string.
- GraphQL transport errors map to 502, problem-not-found maps to 404.
- LLM failure does NOT cache empty ground truth; the client must retry.
- Confidence values remain 0.0–1.0 in the backend; frontend multiplies by 100 for display.
- A single shared helper function `pct()` is used for all confidence-to-percentage conversions.
- Meter component defaults to `max=100`; all callers pass 0–100 values.
- `AnalyzeResponse` exposes `problem_info`, `elo_updates`, `submission_gap` alongside `ast`, `match_result`, `persisted`.
- `run_persistence()` returns full `elo_output` and `gap_output` dicts, not just counts.
- Submission gap only populated when problem context exists (ctx != None); elo_updates always present.

## Relevant Files
- `pathforge/api/routes/analyze.py`: Full `AnalyzeResponse` with `ProblemInfo`, `EloUpdate`, `SubmissionGap` models; constructs canonical patterns from `ctx.accepted_solution_groups`.
- `pathforge/services/persistence.py`: Returns `elo_output` and `gap_output` full dicts for use in response.
- `pathforge-frontend/src/types/api.ts`: `CanonicalPattern`, `ProblemInfo`, `EloUpdate`, `SubmissionGap` interfaces.
- `pathforge-frontend/components/analysis-view.tsx`: Reorganized panel flow: Problem Info → Detected Patterns → Matching Engine (canonical + verdict + reasoning) → Skill Changes (all Elo updates) → Gaps (submission gap + long-term signals).
- `pathforge-frontend/components/charts.tsx`: `Meter({ value, max=100 })` — callers must pass 0–100 values.
