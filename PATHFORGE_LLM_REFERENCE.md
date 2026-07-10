# PathForge — Complete Technical Reference for LLMs

> **Audience:** LLM agents tasked with developing, debugging, reviewing, or extending PathForge.
> **Purpose:** Provide a complete architectural understanding without reading the repository.
> **Status:** Living document — update when subsystems change.
> **Last updated:** 2026-07-07

---

## 1. Project Overview

**PathForge** is a skill-intelligence platform that analyzes Python solutions, detects algorithmic patterns via AST, computes learning gaps, tracks per-pattern Elo ratings, and recommends problems. It is **not** an OJ (online judge); users solve problems on LeetCode and self-report verdicts.

### Primary Objective

Replace blanket problem-drilling with targeted, data-driven learning. The system tells a learner *which pattern they are weak at*, *why*, and *what to solve next*.

### Core Philosophy

- **Pattern-first, not problem-first.**
- **Deterministic analysis at inference time** — AST detectors, not LLM prompt chains, drive analysis.
- **Learner model as a vector of per-pattern Elo ratings** — one rating per canonical pattern (33 total).
- **Stateless detectors** — each detector gets the same AST, runs independently, emits confidence + evidence.
- **No user code is ever executed** — analysis is purely static.

### Intended Workflow

1. User solves a LeetCode problem in Python.
2. Pastes code into PathForge's analysis page, selects verdict (`solved` / `unsolved`).
3. Code is AST-parsed → 33 detectors run → patterns detected → Matching Engine compares against expected patterns → Gap Signal Engine computes weakness scores → Elo Engine updates per-pattern ratings → Recommendation Engine picks next problem.
4. User repeats.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  NEXT.JS FRONTEND (port 3000)                                       │
│  ┌──────────┐  ┌───────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │ Dashboard │  │ Analysis  │  │ Recommendations │  │ Progress     │ │
│  │ /         │  │ /analysis │  │ /recommendations│  │ /progress    │ │
│  └─────┬─────┘  └─────┬─────┘  └───────┬────────┘  └──────┬───────┘ │
│        └───────────────┴────────────────┴──────────────────┘         │
│                           │ AuthProvider                             │
│                    ┌──────┴──────┐                                   │
│                    │ Supabase JS │ (Google OAuth)                     │
│                    └──────┬──────┘                                   │
└───────────────────────────┼───────────────────────────────────────────┘
                            │ Bearer JWT
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│  FASTAPI LAYER (port 8000) — Engine API                               │
│  ┌──────────┐┌──────────┐┌──────────┐┌─────────────┐┌───────────┐   │
│  │ /analyze ││ /gaps    ││ /elo     ││ /recommend  ││ /auth/*   │   │
│  └────┬─────┘└────┬─────┘└────┬─────┘└──────┬──────┘└─────┬─────┘   │
│       │           │           │             │             │          │
│       ▼           ▼           ▼             ▼             ▼          │
│  ┌──────────┐ ┌────────┐ ┌────────┐ ┌───────────────┐ ┌──────────┐  │
│  │ Analysis  │ │ Gap    │ │ Elo    │ │ Recommend     │ │ Auth     │  │
│  │ Service   │ │ Service│ │ Service│ │ Service       │ │ Middleware│  │
│  └────┬──────┘ └────────┘ └────────┘ └───────┬───────┘ └──────────┘  │
│       │                                      │                        │
└───────┼──────────────────────────────────────┼────────────────────────┘
        │                                      │
        ▼                                      ▼
┌──────────────────────────────┐  ┌──────────────────────────┐
│  AST ANALYSIS ENGINE (src/)  │  │  RECOMMENDATION ENGINE    │
│  ┌─────────┐  ┌───────────┐ │  │  (pathforge/)              │
│  │ Parser  │→ │ Detectors │ │  │  ┌──────────────────┐     │
│  │ (ast)   │  │ (33)      │ │  │  │ Recommender (old)│     │
│  └─────────┘  └─────┬─────┘ │  │  │ Recomm Engine    │     │
│                     ▼       │  │  │ (new)            │     │
│  ┌──────────────────────┐   │  │  └──────────────────┘     │
│  │ Coordinator + Output │   │  └──────────────────────────┘
│  └──────────┬───────────┘   │
└─────────────┼────────────────┘
              │
              ▼
┌──────────────────────────────┐
│  MATCHING ENGINE (src/)       │
│  Compares AST output against │
│  expected pattern groups      │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│  GAP SIGNAL ENGINE (pathforge/)               │
│  Combines AST + match + history → gap signals │
└──────┬───────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│  ELO ENGINE (pathforge/)                      │
│  Updates per-pattern Elo using match outcomes │
└──────────────────────────────────────────────┘

┌───────────────────────────────────────────────┐
│  FLASK APP (port 5000) — Submission Pipeline  │
│  POST /api/submit → run_pipeline()            │
│  GET /api/profile/<id>                        │
│  GET /api/recommend/<id>                      │
│  GET /api/problems                            │
│  HTML templates (legacy)                       │
└───────────────────┬───────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────┐
│  SQLITE DATABASE (pathforge.db)                │
│  Tables: users, problems, submissions,          │
│  topic_profiles, recommendations, gap_signals,  │
│  user_pattern_elo, problem_ground_truth         │
└───────────────────────────────────────────────┘
```

### How Components Communicate

| From | To | Method |
|-------|-----|--------|
| Next.js frontend | FastAPI backend | HTTP (fetch) with Bearer JWT |
| Next.js frontend | Supabase (auth) | Supabase JS SDK |
| FastAPI | SQLite | Direct connection (per-request) |
| FastAPI | AST Engine | Python import (`src.ast_detection`) |
| FastAPI | Matching Engine | Python import (`src.matching_engine`) |
| FastAPI | Gap/Elo/Recommend Engines | Python import (`pathforge.*`) |
| Next.js frontend | Flask backend (legacy) | HTTP (fetch) with Bearer JWT |

**There is no message queue, no event bus, no worker pool.** Everything is synchronous Python. The Flask app and FastAPI app are separate processes and do **not** share in-memory state — they both connect to the same SQLite file.

---

## 3. Folder Structure

### `pathforge/` — Flask backend + core engines

| Path | Purpose | Responsibilities | Depends On |
|------|---------|------------------|------------|
| `pathforge/app.py` | Flask app factory | Creates Flask app, registers blueprints, seeds problem bank | `config`, `db/`, `routes/` |
| `pathforge/api/` | FastAPI app (Engine API) | Serves `/analyze`, `/gaps`, `/elo`, `/recommend`, `/auth/*` | `src/ast_detection/`, `src/matching_engine/`, `pathforge/` engines |
| `pathforge/api/routes/` | FastAPI route handlers | `analyze.py`, `gaps.py`, `elo_route.py`, `recommend.py` | `api/services/` |
| `pathforge/api/services/` | FastAPI service layer | `analysis.py`, `gap.py`, `elo.py`, `recommend_service.py`, `loader.py` | Engines + DB |
| `pathforge/auth/` | Authentication middleware | JWT verification (Supabase JWKS), `_ensure_local_user()` | `config`, `db/` |
| `pathforge/db/` | Database layer | `db.py` (connection, init, migrations), `schema.sql`, `profile_manager.py`, `elo.py` | SQLite |
| `pathforge/routes/` | Flask route blueprints | `auth.py`, `problems.py`, `profile.py`, `submissions.py` | `pipeline.py`, `recommender.py`, `db/` |
| `pathforge/ast_engine/` | Older AST engine (legacy) | `extractor.py`, `classifier.py`, `patterns.py`, `sanitizer.py` | None (standalone) |
| `pathforge/llm/` | OpenRouter client | `openrouter_client.py` — calls GPT-4o-mini for ground truth | External API |
| `pathforge/services/` | Auxiliary services | `ground_truth_builder.py` — LLM-based problem labeling | `llm/`, `db/` |
| `pathforge/data/` | Problem bank CSV | `pathforge_problems_fixed.csv` — curated LeetCode problems | Seeding |

### `src/` — AST Detection + Matching Engine (newer)

| Path | Purpose | Responsibilities | Depends On |
|------|---------|------------------|------------|
| `src/ast_detection/` | AST Analysis Engine | Parsing, 33 detectors, coordinator, output pipeline | Python `ast` module |
| `src/ast_detection/detectors/` | 33 detector modules | One file per pattern (e.g., `hash_map_lookup.py`, `dfs_recursive.py`) | `base.py`, `registry.py` |
| `src/ast_detection/detector_interface.py` | Abstract base class | `BaseDetector`, `DetectionResult`, `EvidenceItem` | None |
| `src/ast_detection/registry.py` | Detector registration | `@register_detector` decorator, auto-discovery | `detector_interface.py` |
| `src/ast_detection/detector_manager.py` | Executes all detectors | `detect_all(ast_root)` → list of `DetectionResult` | `registry.py` |
| `src/ast_detection/coordinator.py` | Aggregates + filters results | `aggregate_and_filter()`, `resolve_overlaps()` | `detector_interface.py` |
| `src/ast_detection/output_pipeline.py` | Packages results | `package_results()` → V2 output dict | `registry.py` |
| `src/ast_detection/parser.py` | Sanitize + parse Python | `sanitize_code()`, `Parser.parse()` | Python `ast` |
| `src/ast_detection/run_analysis.py` | Entry point | `ASTAnalysisEngine.analyze(code)` → full pipeline | All above |
| `src/matching_engine/` | Matching Engine | `MatchingEngine.match(llm, ast)` → `MatchResult` | None |

### `pathforge-frontend/` — Next.js Application

| Path | Purpose | Responsibilities |
|------|---------|------------------|
| `app/layout.tsx` | Root layout | AuthProvider, AppShell, globals.css |
| `app/page.tsx` | Dashboard | CategoryElo, WeakestPatterns, RecommendedPreview, ActivityFeed |
| `app/analysis/page.tsx` | Code analysis | `AnalysisView` — code input, AST results, match score, gaps |
| `app/recommendations/page.tsx` | Recommendations | `RecommendationsView` — ranked problem list |
| `app/progress/page.tsx` | Progress tracking | `ProgressView` — per-pattern Elo table |
| `app/profile/page.tsx` | Profile | `ProfileView` — user info, auth status |
| `app/auth/callback/page.tsx` | OAuth callback | Handles PKCE code exchange |
| `components/` | UI components | `dashboard.tsx`, `analysis-view.tsx`, `recommendations-view.tsx`, etc. |
| `src/auth/` | Auth hooks | `AuthProvider.tsx`, `authService.ts`, `supabase.ts` (Proxy wrapper) |
| `src/services/api/` | API client | `client.ts` (fetch wrapper), `endpoints.ts`, `auth.ts` |
| `src/hooks/` | React hooks | `useApi.ts` — `useEloData`, `useGapData`, `useRecommendations`, `useAnalyzeCode` |
| `src/types/` | TypeScript types | `api.ts` — all request/response types |

---

## 4. Major Files

### `pathforge/app.py`
- **Purpose:** Flask application factory.
- **Key exports:** `create_app(test_config=None)`.
- **Responsibilities:** Initializes DB, seeds problems CSV, registers 4 blueprints (auth, problems, profile, submissions), serves 3 HTML templates (`/`, `/practice`, `/dashboard`).
- **Called by:** `Procfile` (gunicorn entry point).
- **Depends on:** `config.py`, `pathforge/db/db.py`, `pathforge/routes/*`.

### `pathforge/api/app.py`
- **Purpose:** FastAPI application factory (engine API).
- **Key exports:** `create_api()`.
- **Responsibilities:** Registers CORSMiddleware, calls `init_db()`, includes 5 routers (auth, analyze, gaps, elo, recommend), serves `/health`.
- **Called by:** `uvicorn` (run directly).
- **Depends on:** `config.py`, `src/ast_detection/`, `src/matching_engine/`, `pathforge/*` engines.

### `pathforge/auth/auth_middleware.py`
- **Purpose:** Supabase JWT verification (FastAPI).
- **Key exports:** `get_current_user()` → `VerifiedUser`, `verify_supabase_token()`.
- **Responsibilities:** Fetches JWKS from Supabase, verifies token signature (RS256/ES256), ensures local user record exists via `_ensure_local_user()`, returns `VerifiedUser(user_id, supabase_id, email)`.
- **Called by:** FastAPI route handlers via `Depends(get_current_user)`.
- **Depends on:** `pathforge/db/db.py`, `config.py`, `httpx`, `python-jose`.

### `pathforge/api/auth_routes.py`
- **Purpose:** FastAPI auth endpoints.
- **Exports:** `GET /auth/session`, `GET /auth/me`, `GET /auth/profile`.
- **Depends on:** `auth_middleware.py`, `db/profile_manager.py`.

### `pathforge/routes/auth.py`
- **Purpose:** Flask auth blueprint (legacy — username/password login).
- **Key exports:** `POST /api/auth/register`, `POST /api/auth/login`, `require_auth` decorator.
- **Responsibilities:** Password hashing with bcrypt, JWT creation via PyJWT (HS256), seed initial topic profiles on register.
- **Called by:** Flask routes via `@require_auth`.
- **Depends on:** `pathforge/db/db.py`, `pathforge/db/profile_manager.py`.

### `pathforge/pipeline.py`
- **Purpose:** Orchestrates submission → recommendation (the critical path).
- **Key exports:** `run_pipeline(user_id, problem_id, verdict, db_path)`.
- **Flow:** `handle_submission()` → mark prior recommendation as acted_on → `get_recommendation()` → `_log_recommendation()` → commit atomically.
- **Called by:** Flasks `POST /api/submit`.
- **Depends on:** `submission_handler.py`, `recommender.py`, `db/profile_manager.py`.

### `pathforge/submission_handler.py`
- **Purpose:** Records a user submission and updates streak/profile.
- **Key exports:** `handle_submission()`.
- **Flow:** Loads problem → extracts pattern → updates topic profile → saves submission row → updates streak.
- **Called by:** `pipeline.py`.
- **Depends on:** `db/profile_manager.py`.

### `pathforge/recommender.py`
- **Purpose:** Legacy recommendation engine (confidence-gated, topic-rotation based).
- **Key exports:** `get_recommendation()`.
- **Flow:** Checks gap_info → if no gap and pass: advance difficulty or rotate topic. If gap detected: confidence gates (specific/topic_hint/general_hint).
- **Called by:** `pipeline.py`, `routes/profile.py`.
- **Depends on:** `db/profile_manager.py`, `pattern_links.py`.

### `pathforge/recommendation_engine.py`
- **Purpose:** Newer recommendation engine (pattern-weakness-based, multi-strategy).
- **Key exports:** `RecommendationEngine.recommend()`.
- **Flow:** Takes user_pattern_elo, gap_signals, recent_submissions → computes weak patterns via `_weak_score()` (gap + Elo deficit) → selects best problem per pattern → enforces category diversity → returns ranked list.
- **Called by:** `api/services/recommend_service.py`.
- **Depends on:** None (pure computation).

### `pathforge/gap_signal_engine.py`
- **Purpose:** Converts AST + match + history into structured gap signals.
- **Key exports:** `GapSignalEngine.compute_signals()`, `GapSignalEngine.persist_signals()`.
- **Flow:** Extracts AST patterns → finds missing patterns → detects weak signals (low confidence, inconsistent performance) → anti-bias filter → weights miss_frequency + recency + confidence penalty → produces gap_strength per pattern.
- **Called by:** (Not currently called in any production path — standalone).

### `pathforge/elo_engine.py`
- **Purpose:** Per-pattern Elo computation with anti-drift.
- **Key exports:** `EloEngine.compute_updates()`, `EloEngine.persist_elos()`.
- **Flow:** Resolves candidate patterns → computes score per pattern (full/partial/no match) → adjusts for gap strength, AST confidence → `_compute_k()` (adaptive K-factor) → `_anti_drift_adjustment()` → produces updates.
- **Called by:** (Not currently called in any production path — standalone).

### `src/ast_detection/run_analysis.py`
- **Purpose:** Main entry point for AST Analysis Engine.
- **Key exports:** `ASTAnalysisEngine.analyze(code_string)`, `run_analysis()`.
- **Flow:** Parse → detect_all → aggregate_and_filter → package_results.
- **Called by:** `pathforge/api/services/analysis.py`.

### `src/matching_engine/matching_engine.py`
- **Purpose:** Compares AST-detected patterns against expected pattern groups.
- **Key exports:** `MatchingEngine.match(llm_output, ast_output)`.
- **Flow:** Normalizes AST and LLM groups → computes group matches → confidence score → decides FULL_MATCH / PARTIAL_MATCH / NO_MATCH → finds unmatched patterns.
- **Called by:** `pathforge/api/services/analysis.py`.

### `pathforge/db/db.py`
- **Purpose:** Database initialization, connections, and lightweight migrations.
- **Key exports:** `get_connection()`, `connect()` (context manager), `init_db()`.
- **Responsibilities:** Reads `schema.sql`, applies `_ensure_*` tables (gap_signals, user_pattern_elo, problem_ground_truth), adds columns for supabase_id, experience_level, confident_areas, onboarding_complete, etc.
- **Called by:** Both FastAPI (`create_api()`) and Flask (`create_app()`), also every route handler.

### `pathforge/db/profile_manager.py`
- **Purpose:** User profile CRUD, Elo updates, weakest topic computation.
- **Key exports:** `seed_initial_topic_profiles()`, `update_topic_profile()`, `get_user_profile()`, `get_weakest_topics()`, `get_recommendable_patterns()`.
- **Called by:** `pipeline.py`, `submission_handler.py`, `routes/profile.py`, `recommender.py`.

### `pathforge/db/elo.py`
- **Purpose:** Simple Elo update for topic profiles.
- **Key exports:** `update_elo(current_rating, difficulty, outcome)`, `outcome_from_submission()`, `calculate_expected()`.
- **Called by:** `profile_manager.py`.

### `pathforge/services/ground_truth_builder.py`
- **Purpose:** LLM-powered problem labeling pipeline.
- **Key exports:** `build_ground_truth(problem_id, problem_description, connection)`.
- **Flow:** Calls `openrouter_client.call_llm()` → normalizes patterns to canonical names → stores in `problem_ground_truth` table.
- **Depends on:** `llm/openrouter_client.py`, `ast_engine/patterns.py`.

### `pathforge/llm/openrouter_client.py`
- **Purpose:** OpenRouter API client for GPT-4o-mini.
- **Key exports:** `call_llm(problem_text)`.
- **Flow:** Builds prompt (pattern classification task) → POST to OpenRouter with retry (2) → parses JSON response → returns `{"patterns": [...], "confidence": {...}}`.
- **Called by:** `ground_truth_builder.py`.

---

## 5. Frontend

### Routing
Next.js App Router with 5 pages:

| Path | Component | Purpose |
|------|-----------|---------|
| `/` | `DashboardPage` | Skill overview, Elo chart, weakest patterns, recommended preview |
| `/analysis` | `AnalysisView` | Code input, AST results, match engine, gap signals |
| `/recommendations` | `RecommendationsView` | Ranked problem list with difficulty filter |
| `/progress` | `ProgressView` | Per-pattern Elo table, strong/weak clusters |
| `/profile` | `ProfileView` | User info, auth status, pattern profiles |
| `/auth/callback` | `AuthCallbackPage` | OAuth PKCE code exchange |

### Authentication Flow (Frontend)

1. Landing page shows "Sign in with Google" button → calls `signInWithGoogle()` (`src/auth/authService.ts`).
2. `signInWithGoogle()` calls `supabase.auth.signInWithOAuth({ provider: 'google' })` with `redirectTo: /auth/callback`.
3. Browser redirects to Google → Google redirects back to `/auth/callback?code=...`.
4. `AuthCallbackPage` calls `supabase.auth.exchangeCodeForSession(code)`.
5. On success, `AuthProvider` (via `onAuthStateChange`) picks up the session, sets `user`, `session`, calls `fetchMe()` to load profile.
6. `setAccessToken(token)` stores the JWT in `_accessToken` (module-level variable in `client.ts`).
7. All subsequent `apiRequest()` calls attach `Authorization: Bearer <token>`.

### Context Providers
- **`AuthProvider`** (`src/auth/AuthProvider.tsx`): Wraps entire app. Exposes `{ user, session, profile, loading, signOut }` via `useAuth()`.

### API Layer
- **`src/services/api/client.ts`**: `apiRequest<T>(path, options)` — fetch wrapper. Attaches Bearer token from `_accessToken`, throws `ApiError` on non-2xx.
- **`src/services/api/endpoints.ts`**: Typed functions for `/analyze`, `/gaps`, `/elo`, `/recommend`.
- **`src/services/api/auth.ts`**: `fetchMe()` → `/auth/me`, `fetchAuthProfile()` → `/auth/profile`.

### Hooks
- **`useApiData<T>(fetcher, deps, skip)`**: Generic hook returning `{ data, loading, error, refresh }`.
- **`useAuthProfile()`** → `fetchAuthProfile()`
- **`useEloData(userId)`** → `fetchElo()`
- **`useGapData(userId)`** → `fetchGaps()`
- **`useRecommendations(userId)`** → `fetchRecommendations()`
- **`useAnalyzeCode()`**: Mutation hook returning `{ result, loading, error, run }`.

### Major Components

| Component | File | Purpose |
|-----------|------|---------|
| `AppShell` | `components/app-shell.tsx` | Sidebar nav, user menu, auth gate (shows login page if no user) |
| `AnalysisView` | `components/analysis-view.tsx` | Code textarea, run button, AST patterns panel, match score, gap signals, Elo preview |
| `DashboardPage` | `app/page.tsx` | Uses `CategoryElo`, `WeakestPatterns`, `RecommendedPreview`, `ActivityFeed` |
| `CategoryElo` | `components/dashboard.tsx` | Bar chart of all pattern Elos |
| `WeakestPatterns` | `components/dashboard.tsx` | Top 5 lowest Elo patterns |
| `RecommendedPreview` | `components/dashboard.tsx` | Top 4 recommendations |
| `RecommendationsView` | `components/recommendations-view.tsx` | Full recommendation list with difficulty filter |
| `ProgressView` | `components/progress-view.tsx` | Per-pattern Elo table, strong/weak clusters |
| `ProfileView` | `components/profile-view.tsx` | User info, auth status, pattern profiles list |

### Current UI Workflow
1. User opens app → sees landing page → signs in with Google.
2. Redirects to dashboard → sees empty state ("Submit code to see activity").
3. Navigates to `/analysis` → pastes Python code → clicks "Run Analysis".
4. Sees AST-detected patterns, match score, gap signals, Elo preview.
5. Navigates to `/recommendations` → sees ranked problem list.
6. User solves recommended problem on LeetCode → returns → marks as solved → submits again.

### State Management
- **No React state management library** (no Redux, Zustand, etc.).
- Auth state via React Context (`AuthProvider`).
- API data via per-component `useState` + `useEffect` in `useApiData`.
- Token stored in a module-level variable (`_accessToken` in `client.ts`).

### Current Shortcomings
- No problem submission UI exists in the frontend (no `/api/submit` call is wired up).
- The `AnalysisView` calls `/analyze` but the results are read-only — no actual submission/verdict flow.
- `ActivityFeed` shows static empty state.
- No loading skeletons (only text "Loading...").
- No error boundaries.
- The `_accessToken` module variable is lost on page navigation (but `AuthProvider` resets it via `onAuthStateChange`).

---

## 6. Backend

### Why Both FastAPI and Flask Exist

The project transitioned from Flask to FastAPI over time. The Flask app was the original backend — it serves the submission pipeline, legacy HTML templates (index.html, dashboard.html, practice.html), and the older username/password auth. The FastAPI app was added later to serve the engine endpoints (analysis, gaps, Elo, recommendations) with async-capable middleware.

**Current split:**
- **FastAPI** (port 8000): Modern engine API. Serves `/analyze`, `/gaps`, `/elo`, `/recommend`, `/auth/*`. Uses `Depends(get_current_user)` for auth. The primary API used by the Next.js frontend.
- **Flask** (port 5000): Legacy pipeline. Serves `/api/submit`, `/api/profile/<id>`, `/api/recommend/<id>`, `/api/problems`, and HTML templates. The Next.js frontend does **not** currently call Flask endpoints directly.

**Why both remain:** The submission pipeline (`pipeline.py` → `submission_handler.py` → `recommender.py`) is deeply tied to Flask blueprints and has not been migrated. The FastAPI `run_pipeline()` path (`api/services/analysis.py` → AST + Matching Engine) does **not** call the Flask pipeline — it only runs AST analysis and returns results.

### FastAPI — Current Responsibilities

| File | Route | Action |
|------|-------|--------|
| `api/routes/analyze.py` | `POST /analyze` | Runs AST + Matching Engine |
| `api/routes/gaps.py` | `POST /gaps` | Loads stored gap signals |
| `api/routes/elo_route.py` | `POST /elo` | Loads stored Elo ratings |
| `api/routes/recommend.py` | `POST /recommend` | Runs Recommendation Engine |
| `api/auth_routes.py` | `GET /auth/session`, `/auth/me`, `/auth/profile` | Auth verification |

### Flask — Current Responsibilities

| File | Route | Action |
|------|-------|--------|
| `routes/auth.py` | `POST /api/auth/register`, `POST /api/auth/login` | Legacy auth |
| `routes/problems.py` | `GET /api/problems`, `GET /api/problems/<id>` | Problem bank |
| `routes/submissions.py` | `POST /api/submit` | Submission + recommendation pipeline |
| `routes/profile.py` | `GET /api/profile/<id>`, `GET /api/recommend/<id>` | User profile, standalone recommendation |

### Database Initialization

Both apps call `init_db()` on startup. The function:
1. Reads `pathforge/db/schema.sql`.
2. Creates all tables (IF NOT EXISTS).
3. Runs `_apply_lightweight_migrations()` which adds missing columns/tables for backward compatibility with older SQLite files.

Since both apps share the same SQLite file, double initialization is harmless (all statements use IF NOT EXISTS).

### Authentication Middleware

**FastAPI:** `auth_middleware.py` uses `HTTPBearer` scheme, fetches JWKS from Supabase, verifies JWT with `python-jose`, looks up or creates local user, returns `VerifiedUser`.

**Flask:** `routes/auth.py` defines a `@require_auth` decorator that decodes a simple HS256 JWT (signed with `config.JWT_SECRET`). This JWT is created on `/api/auth/login` or `/api/auth/register`. It is **not** the same JWT as the Supabase token.

**Implication:** The Flask and FastAPI auth systems are completely independent. The Flask `@require_auth` decorator verifies a self-signed JWT. The FastAPI `get_current_user` verifies a Supabase JWT. The frontend currently uses Supabase auth only, so Flask endpoints (if called directly) would need a different token.

---

## 7. Authentication

### Complete Flow

1. **User clicks "Sign in with Google"** on the Next.js frontend.
2. `authService.signInWithGoogle()` calls `supabase.auth.signInWithOAuth({ provider: 'google' })` with PKCE flow.
3. Browser redirects to Google OAuth → user consents → Google redirects to `/auth/callback?code=<pkce_code>`.
4. **`AuthCallbackPage`** exchanges the code for a session via `supabase.auth.exchangeCodeForSession(code)`.
5. **Supabase returns** `{ session: { access_token, refresh_token, user } }`.
6. **`AuthProvider`** (via `onAuthStateChange`) receives the session and calls `setAccessToken(access_token)`.
7. **`AuthProvider`** calls `fetchMe()` → `GET /auth/me` with `Authorization: Bearer <access_token>`.
8. **FastAPI `auth_middleware.verify_supabase_token()`** fetches JWKS from `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json`, verifies the token (RS256/ES256), extracts `sub` (Supabase user ID).
9. **`_ensure_local_user()`** looks up `supabase_id` in SQLite `users` table. If not found, creates a new user row with username = `supabase_id`, email from JWT, empty password_hash.
10. **Route handler** returns user profile data.

### Key Details
- Supabase project ref: `rrriujagbpfhrqzjcxfa`
- Supabase URL: `https://rrriujagbpfhrqzjcxfa.supabase.co`
- Auth flow: PKCE (no client secret needed)
- Token audience: `authenticated`
- JWKS cache: Module-level `_JWKS_CACHE` (never invalidated — lives for process lifetime)
- Local user creation: `_ensure_local_user()` in `auth_middleware.py:112-166`

### Common Failure Points

| Problem | Likely Cause | File to Inspect |
|---------|-------------|-----------------|
| OAuth redirect loop | PKCE code verifier cookie missing (cross-origin) | `authService.ts`, `supabase.ts` |
| 401 "Missing kid in token header" | Token is not a Supabase JWT (e.g., expired, wrong provider) | `auth_middleware.py:78-81` |
| 401 "No matching JWK found" | JWKS endpoint unreachable or token signed with different key | `auth_middleware.py:83-90` |
| 500 "Database error during user insert" | UNIQUE constraint on email or supabase_id | `auth_middleware.py:138-163` |
| User created without profile | `_ensure_local_user()` creates user but no topic_profiles seeded (supabase flow skips seed) | `auth_middleware.py:138-163` |
| Auth works on FastAPI but not Flask | Flask uses a different JWT secret and doesn't verify Supabase tokens | `routes/auth.py:38-45` |

---

## 8. Database

### Current Schema

**SQLite** at `pathforge.db` (project root) with 8 tables:

#### `users`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `username` | TEXT UNIQUE | Set to `supabase_id` for OAuth users |
| `email` | TEXT UNIQUE | From JWT or placeholder |
| `password_hash` | TEXT | Empty string for OAuth users |
| `display_name` | TEXT | From Google profile |
| `experience_level` | TEXT | `beginner` (default) |
| `confident_areas` | TEXT | JSON array of broad topics |
| `onboarding_complete` | INTEGER | 0/1 |
| `last_recommendation_id` | INTEGER | FK → recommendations.id |
| `current_streak` | INTEGER | Consecutive days |
| `last_submission_date` | TEXT | ISO date |
| `supabase_id` | TEXT UNIQUE | For OAuth users |
| `created_at`, `updated_at` | TEXT | ISO 8601 |

#### `problems`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | LeetCode problem ID |
| `title`, `difficulty`, `topics`, `pattern`, `test_cases` | TEXT | pattern is JSON array |
| `link`, `acceptance_rate`, `premium_only` | TEXT/REAL/INT | |
| `category`, `likes`, `dislikes`, `similar_questions` | TEXT/INT/TEXT | |

#### `submissions`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `user_id` | INTEGER FK | → users.id |
| `problem_id` | INTEGER FK | → problems.id |
| `code_text` | TEXT | Stored as `"self-reported"` (not actual code) |
| `verdict` | TEXT | pass/fail/error/tle |
| `detected_pattern`, `expected_pattern`, `target_pattern` | TEXT | |
| `detected_confidence`, `diagnosis_confidence` | REAL | 0.0–1.0 |
| `gap_identified` | INTEGER | 0/1 |
| `topic` | TEXT | |
| `attempt_number` | INTEGER | Per-problem attempt count |
| `submitted_at` | TEXT | ISO 8601 |

#### `topic_profiles`
| Column | Type | Notes |
|--------|------|-------|
| `user_id` | INTEGER FK | → users.id |
| `topic` | TEXT | Pattern name |
| `elo_rating` | REAL | 800.0 default, min 400.0 |
| `attempt_count`, `pass_count` | INTEGER | |
| `pattern_match_count` | INTEGER | |
| `accuracy` | REAL | 0.0–1.0 |
| `recent_failures` | INTEGER | |
| `last_attempt_at` | TEXT | |
| PRIMARY KEY | | (user_id, topic) |

#### `recommendations`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `user_id`, `problem_id` | INTEGER FK | |
| `topic` | TEXT | |
| `reason` | TEXT | |
| `confidence_tier` | TEXT | specific/topic_hint/general_hint |
| `acted_on`, `followed` | INTEGER | 0/1 |
| `elo_delta_after` | REAL | Nullable |

#### `gap_signals`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `user_id` | INTEGER FK | |
| `pattern_id` | TEXT | |
| `gap_strength` | REAL | 0.0–1.0 |
| `frequency` | INTEGER | |
| `last_seen` | TEXT | |
| UNIQUE | | (user_id, pattern_id) |

#### `user_pattern_elo`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `user_id` | INTEGER FK | |
| `pattern_id` | TEXT | |
| `elo` | REAL | 1200.0 default, min 400.0 |
| UNIQUE | | (user_id, pattern_id) |

#### `problem_ground_truth`
| Column | Type | Notes |
|--------|------|-------|
| `problem_id` | INTEGER PK FK | → problems.id |
| `patterns` | TEXT | JSON array |
| `confidence` | TEXT | JSON dict |
| `created_at`, `updated_at` | TEXT | |

### Relationships

```
users ──1:N──→ submissions
users ──1:N──→ topic_profiles
users ──1:N──→ recommendations
users ──1:N──→ gap_signals
users ──1:N──→ user_pattern_elo
users.recommendation_id ──→ recommendations.id (nullable)
problems ──1:N──→ submissions
problems ──1:1──→ problem_ground_truth
```

### Migration Process

There is **no formal migration system**. The `_apply_lightweight_migrations()` function in `db.py` checks for missing columns/tables and adds them. This is additive only (never drops or renames columns). The pattern is:
1. Check `PRAGMA table_info(table)` for column existence.
2. `ALTER TABLE ... ADD COLUMN` if missing.
3. Create new tables if they don't exist.

### SQLite vs Supabase

| Data | Location | Notes |
|------|----------|-------|
| User accounts | SQLite + Supabase Auth | Supabase for OAuth, SQLite for profile data |
| Problem bank | SQLite | Seeded from CSV |
| Submissions | SQLite | |
| Topic profiles | SQLite | |
| Recommendations | SQLite | |
| Gap signals | SQLite | |
| Pattern Elo | SQLite | |
| Ground truth | SQLite | |
| Auth tokens/sessions | Supabase Auth only | Not stored locally |

**Known inconsistency:** The `.env` file contains `DATABASE_URL=postgresql://...` for Supabase Postgres, but the actual code only uses SQLite. The Supabase Postgres is **not connected** to the application. Only Supabase Auth is used.

---

## 9. Analysis Engine

The analysis pipeline converts Python source code into structured pattern detections.

### Stage 1: Parse (sanitizer → parser)

| | |
|---|---|
| **File** | `src/ast_detection/parser.py` |
| **Input** | Raw Python source code string |
| **Output** | `ast.AST` root node |
| **Action** | 1. `sanitize_code()` — blocks eval/exec/dangerous imports, detects non-Python. 2. `ast.parse()` — syntax parse. |
| **Errors** | `ValueError` for unsafe code or syntax errors. |

### Stage 2: AST Detection (33 detectors)

| | |
|---|---|
| **File** | `src/ast_detection/detectors/*.py` (33 files) |
| **Input** | `ast.AST` root node |
| **Output** | `List[DetectionResult]` — one per detector |
| **Action** | Each detector walks the AST looking for pattern-specific node shapes. Returns `{ pattern_id, confidence, evidence[] }`. |
| **Design** | Stateless, deterministic, isolated. No detector calls another. |
| **Orchestration** | `DetectorManager.detect_all(ast_root)` in `detector_manager.py`. |
| **Registration** | Each detector has a `pattern_id` class attribute and uses `@register_detector` decorator. Detection happens in `registry.py` → `DetectorRegistry`. |

### Stage 3: Coordinator (aggregate + filter)

| | |
|---|---|
| **File** | `src/ast_detection/coordinator.py` |
| **Input** | `List[DetectionResult]` (one per detector) |
| **Output** | Filtered + sorted `List[DetectionResult]` |
| **Action** | Removes results with empty evidence. Sorts by confidence descending. Resolves overlapping detections (basic: keeps unique pattern_id with highest confidence). |
| **Note** | Current overlap resolution is minimal. Does NOT use taxonomy hierarchy. |

### Stage 4: Output Pipeline

| | |
|---|---|
| **File** | `src/ast_detection/output_pipeline.py` |
| **Input** | Filtered `List[DetectionResult]` |
| **Output** | `Dict{"detected_patterns": [...], "engine_version": "2.0.0", ...}` |
| **Action** | Converts to serializable dict with metadata. |

### Stage 5: Matching Engine

| | |
|---|---|
| **File** | `src/matching_engine/matching_engine.py` |
| **Input** | `ast_output` (detected patterns) + synthetic `llm_output` (detected patterns treated as expected groups) |
| **Output** | `MatchResult` with `match_result` (FULL_MATCH/PARTIAL_MATCH/NO_MATCH), `matched_groups`, `unmatched_patterns`, `confidence_score` |
| **Action** | 1. Normalize AST patterns to `{pattern_id: confidence}`. 2. Build "LLM groups" from detected patterns (each group = `[pattern_id]` — a singleton). 3. Compute group matches (overlap, coverage). 4. Compute confidence from matched groups, subtract penalty for extra AST patterns. 5. Decide match result. |
| **Key insight** | The Matching Engine compares **detected patterns** against **expected pattern groups**. But currently, the "expected" groups are derived from the detected patterns themselves (singleton groups). This means the match is always FULL_MATCH if any pattern is detected. The true LLM-based ground truth is not integrated (see Ground Truth). |
| **Called by** | `api/services/analysis.py:48-49` |

### Stage 6: Gap Signal Engine

| | |
|---|---|
| **File** | `pathforge/gap_signal_engine.py` |
| **Input** | `ast_output`, `match_result`, `submission_history` |
| **Output** | Dict with `gap_signals[]` and `summary{strong_gaps, moderate_gaps, weak_gaps}` |
| **Action** | 1. `_extract_ast_patterns()` — flattens AST output. 2. `_extract_missing_patterns()` — finds unmatched patterns. 3. `_detect_weak_signals()` — low-confidence patterns, inconsistent performance. 4. Anti-bias filter (skip if recent high-confidence on pattern). 5. Weight miss_frequency + recency + confidence penalty → gap_strength. |
| **Current status** | Engine exists and is tested but is NOT called in any active request path. |

### Stage 7: Elo Engine

| | |
|---|---|
| **File** | `pathforge/elo_engine.py` |
| **Input** | `gap_signals`, `match_result`, `ast_output`, `current_elos`, `pattern_histories` |
| **Output** | Dict with `pattern_elo_updates[]` and `global_summary` |
| **Action** | 1. Resolves candidate patterns from gaps + AST + unmatched. 2. Computes score per pattern (FULL_MATCH→1.0, PARTIAL→0.5, NO_MATCH→0.0). 3. Adjusts for gap strength, AST confidence. 4. Adaptive K-factor based on gap strength and history length. 5. Anti-drift adjustment (repeated same result → score decay/saturation). 6. Persists to `user_pattern_elo` table. |
| **Current status** | Engine exists but is NOT called in any active request path. |

---

## 10. Ground Truth Layer

### Current Implementation

The Ground Truth system exists but is **not integrated** into the analysis pipeline. It lives in:

- **`pathforge/services/ground_truth_builder.py`**: Orchestrator — calls LLM, normalizes patterns, stores in DB.
- **`pathforge/llm/openrouter_client.py`**: HTTP client for OpenRouter's GPT-4o-mini.
- **`problem_ground_truth` table**: Stores `problem_id → patterns[] + confidence{}`.

### LLM Generation

`build_ground_truth(problem_id, problem_description, connection)`:
1. Calls `openrouter_client.call_llm(problem_description)` with a prompt asking to identify algorithmic patterns required to solve the problem.
2. LLM returns `{"patterns": ["pattern_1", ...], "confidence": {"pattern_1": 0.9}}`.
3. Patterns are normalized to canonical snake_case names (from `ALL_PATTERNS` in `patterns.py`).
4. Non-canonical patterns are discarded.
5. Results are stored in `problem_ground_truth` via INSERT OR REPLACE.

### Caching
- Results are persisted in SQLite (`problem_ground_truth` table).
- No TTL, no staleness check, no invalidation.
- If the table already has a row for a `problem_id`, it is overwritten on next `build_ground_truth` call.

### Current Missing Pieces

1. **No caller**: No production code calls `build_ground_truth()`. There is no scheduled job, no API endpoint, no seeding script that generates ground truth for the problem bank.
2. **Not integrated with Matching Engine**: The Matching Engine expects `llm_output` with `accepted_solution_groups` but the analysis service (`api/services/analysis.py`) currently synthesizes groups from detected patterns instead of querying ground truth.
3. **No ground truth seeding**: The `problem_ground_truth` table is nearly empty (or empty) in practice.
4. **No confidence thresholding**: The LLM's confidence values are stored but never used in scoring decisions.

### Expected Workflow

1. An offline script or admin endpoint calls `build_ground_truth()` for all problems in the bank.
2. The analysis service loads ground truth patterns for the submitted problem ID.
3. The Matching Engine compares AST-detected patterns against ground truth patterns (not synthetic groups).
4. Gap signals, Elo updates, and recommendations become more accurate because the expected patterns come from LLM analysis, not self-report.

---

## 11. Recommendation Engine

There are **two** recommendation systems:

### A) `recommender.py` (Legacy — active in submission pipeline)

**Input:** `submission_result`, `problem_record`, DB connection.
**Output:** Dict with `tier`, `problem`, `explanation`, `confidence`, `topic`, `difficulty`.

**Logic:**
1. If gap detected: confidence gates output — `specific` (≥0.75) → pick problem for gap pattern; `topic_hint` (≥0.55) → general topic advice; `general_hint` → vague suggestion.
2. If no gap and solved: advance difficulty or rotate topic if 3+ consecutive passes on same pattern.
3. If no gap and failed: decrease difficulty or rotate topic if 3+ recent failures.
4. **Topic rotation**: `_rotate_topic()` picks the weakest topic with available problems (via `get_weakest_topics()`).
5. **Problem selection**: `_select_problem()` picks highest-acceptance unsolved problem for a (topic, difficulty) pair.

**Key functions:**

| Function | Line | Purpose |
|----------|------|---------|
| `get_recommendation()` | 14 | Main orchestrator |
| `_select_problem()` | 126 | SQL query for best available problem |
| `_check_pattern_lock()` | 150 | Returns True if 3+ consecutive same verdict |
| `_rotate_topic()` | 221 | Weakest topic with available problems |
| `_build_explanation()` | 244 | Deterministic explanation string |
| `_recommendation()` | 280 | Normalized response dict builder |

### B) `recommendation_engine.py` (Newer — active in FastAPI /recommend)

**Input:** `user_pattern_elo`, `gap_signals`, `recent_submissions` (loaded from DB by `recommend_service.py`).
**Output:** Dict with `recommended_problems[]` and `summary`.

**Logic:**
1. `_compute_weak_patterns()`: For each pattern, compute `_weak_score(gap_strength, elo_deficit)`. Solved patterns get 0.5× multiplier. Patterns with no problems are skipped.
2. `_determine_strategy()`: Based on submission count and gap distribution: `cold_start_exploration`, `reinforce_weakest`, `broaden_coverage`, `balanced_maintenance`.
3. For each weak pattern (up to `MAX_RECOMMENDATIONS=5`): Apply novelty bonus, recency penalty, category diversity bonus → priority. Pick best unsolved problem (highest acceptance rate).
4. Enforce minimum category diversity (2 categories) if needed.
5. Return ranked list.

**Scoring details:**
- `_weak_score(gap, elo) = gap * 0.5 + elo_deficit * 0.5`
- `elo_deficit(elo) = max(0, (1200 - elo) / 1200)`
- `_expected_learning_gain(wscore, is_unsolved) = min(wscore * 0.7 + (0.2 if unsolved), 1.0)`
- Difficulty bounds: Easy (Elo < 1000), Medium (1000–1300), Hard (>1300)

### Current Limitations

- **`recommender.py`** is tightly coupled to the Flask submission pipeline and uses `topic_profiles.elo_rating` (not `user_pattern_elo`).
- **`recommendation_engine.py`** uses `user_pattern_elo` (Elo Engine output) but that table is nearly always empty because the Elo Engine is not invoked.
- Neither engine uses `problem_ground_truth` data.
- The `elo` module in `profle_manager.py` and `recommendation_engine.py` use different Elo scales (800/1200 vs 1200 starting).
- The recommendation strategy does not consider problem similarity, prerequisite chains, or session fatigue.

---

## 12. API Reference

### FastAPI (port 8000)

#### `GET /auth/session`
- **Purpose:** Verify current token.
- **Auth:** Bearer JWT.
- **Response:** `{"authenticated": true, "user_id": int, "supabase_id": str, "email": str}`

#### `GET /auth/me`
- **Purpose:** Get current user profile.
- **Auth:** Bearer JWT.
- **Response:** Full user row (id, username, email, display_name, experience_level, confident_areas, onboarding_complete, current_streak, etc.)

#### `GET /auth/profile`
- **Purpose:** Get Elo topic profiles for current user.
- **Auth:** Bearer JWT.
- **Response:** `{"profiles": [...topic_profiles], "overall_elo": float}`

#### `POST /analyze`
- **Request:** `{"user_id": str, "code": str, "language": str}`
- **Response:** `{"ast": {...output_pipeline}, "match_result": {...match_result}}`
- **Auth:** None (no middleware on this route — see note below).
- **Called by:** Frontend `useAnalyzeCode().run()`.

**Note:** The `/analyze` route does **not** use `Depends(get_current_user)`. It accepts any `user_id` string without verification.

#### `POST /gaps`
- **Request:** `{"user_id": int}`
- **Response:** `{"gap_signals": [...], "summary": {...}}`
- **Auth:** None.

#### `POST /elo`
- **Request:** `{"user_id": int}`
- **Response:** `{"pattern_elo": {...}, "summary": {...}}`
- **Auth:** None.

#### `POST /recommend`
- **Request:** `{"user_id": int}`
- **Response:** `{"recommended_problems": [...], "summary": {...}}`
- **Auth:** None.

#### `GET /health`
- **Response:** `{"status": "ok", "system": "PathForge API v2"}`

### Flask (port 5000)

#### `POST /api/auth/register`
- **Request:** `{"username", "email", "password", "display_name"?, "experience_level"?}`
- **Auth:** None.
- **Response:** `{"user_id", "token", "username", "seed"}`

#### `POST /api/auth/login`
- **Request:** `{"username"|"email", "password"}`
- **Auth:** None.
- **Response:** `{"user_id", "token", "username"}`

#### `GET /api/problems`
- **Query:** `?page=1&per_page=20&difficulty=&topic=&search=`
- **Auth:** `@require_auth` (Flask JWT).
- **Response:** `{"items": [...problems], "page", "per_page", "total"}`

#### `GET /api/problems/<id>`
- **Auth:** `@require_auth`.
- **Response:** Full problem without test_cases body, with `test_case_count`.

#### `POST /api/submit`
- **Request:** `{"user_id", "problem_id", "verdict"}` (verdict: "solved"|"unsolved")
- **Auth:** `@require_auth` (verifies `user_id` matches token).
- **Response:** `{"verdict", "pattern_updated", "elo_change", "next_recommendation", "explanation"}`

#### `GET /api/profile/<user_id>`
- **Auth:** `@require_auth`.
- **Response:** `{"profiles", "overall_elo", "weakest_topics", "recent_submissions", "stats"}`

#### `GET /api/recommend/<user_id>`
- **Auth:** `@require_auth`.
- **Query:** `?refresh=true` to force new recommendation.
- **Response:** Same format as `recommender.py` output.
- **Note:** Returns last unacted recommendation if available (avoid recomputing on page load).

---

## 13. Request Lifecycles

### 1. Login

```
1. User clicks "Sign in with Google" on frontend
2. Frontend: authService.signInWithGoogle()
   → supabase.auth.signInWithOAuth({ provider: 'google' })
3. Browser redirects to Google OAuth
4. Google redirects to /auth/callback?code=<pkce_code>
5. Frontend: AuthCallbackPage
   → exchangeCodeForSession(code)
6. Supabase returns { session: { access_token, refresh_token, user } }
7. AuthProvider.onAuthStateChange fires
   → setUser(user), syncToken(access_token)
   → calls fetchMe() → GET /auth/me (FastAPI)
8. FastAPI: auth_middleware.get_current_user()
   → verify_supabase_token(token) [JWKS fetch + verify]
   → _ensure_local_user(payload) [lookup or INSERT INTO users]
   → returns VerifiedUser
9. FastAPI route handler queries users table → returns profile
10. Frontend: AuthProvider.profile set → AppShell shows sidebar
11. User redirected to dashboard (/)
```

### 2. Run Analysis (no submission — just analysis)

```
1. User pastes code in /analysis page, clicks "Run Analysis"
2. Frontend: useAnalyzeCode().run({ user_id, code, language })
   → apiRequest('POST /analyze', body)
3. FastAPI: analysis_service.run_analysis(code, language)
   → ASTAnalysisEngine.analyze(code)
     → Parser.parse(code) → ast.AST
     → DetectorManager.detect_all(ast_root) → 33 DetectionResults
     → Coordinator.aggregate_and_filter() → filtered + sorted
     → OutputPipeline.package_results() → dict
   → (synthetic) llm_groups = [[pattern_id] for each detected pattern]
   → MatchingEngine.match(llm_input, ast_for_matching)
     → MatchResult { match_result, matched_groups, unmatched_patterns... }
4. Returns { ast: {...}, match_result: {...} }
5. Frontend: renders AST patterns panel + match score + gap signals (from /gaps)
```

### 3. Full Submission Pipeline (Flask — legacy active path)

```
1. Frontend calls POST /api/submit (not currently wired in Next.js frontend)
2. Flask: @require_auth verifies HS256 JWT
3. flask/submissions.py validates payload → run_pipeline()
4. handle_submission():
   → loads problem row
   → extracts first pattern from JSON
   → update_topic_profile() [upsert topic_profiles, compute Elo]
   → _save_submission() [INSERT INTO submissions]
   → _update_user_streak() [daily streak]
5. _mark_last_recommendation_acted_on() [UPDATE recommendations SET acted_on=1]
6. get_recommendation():
   → checks gap_info (always "gap_detected": false for manual submits)
   → if pass: advance difficulty or rotate topic
   → if fail: decrease difficulty or rotate topic
   → _select_problem() [SQL: unsolved → highest acceptance]
7. _log_recommendation() [INSERT INTO recommendations + UPDATE users]
8. connection.commit() [atomic]
9. Returns { verdict, pattern_updated, elo_change, next_recommendation, explanation }
```

### 4. Recommendation (FastAPI /recommend)

```
1. Frontend calls POST /recommend (on /recommendations page load)
2. FastAPI: recommend_service.get_recommendations(user_id)
3. Loads: user_info, problem_bank, user_pattern_elo, gap_signals, submissions
4. Instantiates RecommendationEngine(problem_bank)
5. engine.recommend():
   → _analyze_submissions() → solved_patterns, recent_patterns
   → _compute_weak_patterns(elos, gap_map, solved_patterns)
   → if empty → _cold_start_fallback()
   → _determine_strategy()
   → For each weak pattern: _select_best_problem() → append with reason/score
   → _enforce_diversity() if < 2 categories
6. Returns { recommended_problems[], summary }
```

### 5. Ground Truth Generation

```
1. (Manual / scheduled — not wired to any request)
2. build_ground_truth(problem_id, description, connection)
3. call_llm(description) → GPT-4o-mini returns { patterns, confidence }
4. _normalize_patterns(patterns, confidence):
   → lowercase, snake_case
   → filter to canonical ALL_PATTERNS only
5. _store_ground_truth():
   → INSERT OR REPLACE INTO problem_ground_truth
6. Returns canonical pattern list
```

### 6. Problem Search

```
1. Frontend calls GET /api/problems?difficulty=Easy&topic=hash_map
2. Flask: problems_bp → require_auth
3. Builds SQL WHERE from query params (difficulty/topic/title search)
4. Paginated: LIMIT per_page OFFSET offset
5. Returns { items: [...], page, per_page, total }
```

### 7. Submission (as it should work — not fully implemented)

The intended full loop that connects the new engines is:
```
1. User submits code + verdict
2. AST Analysis → detect patterns
3. Matching Engine → compare against problem_ground_truth (LLM-labeled)
4. Gap Signal Engine → compute gap_strength per pattern
5. Elo Engine → update user_pattern_elo
6. Recommendation Engine → pick next problem
7. Persist gap_signals + user_pattern_elo + recommendation + submission atomically
```

**Status:** Step 2 runs (but with synthetic groups, not ground truth). Steps 4-5 engines exist but are not wired. Step 6 runs from stored data (not from fresh analysis).

---

## 14. Important Data Models

### `User` (SQLite `users` table)
- `id: int` — local primary key
- `supabase_id: str` — Supabase Auth user UUID
- `username: str` — for OAuth users, same as `supabase_id`
- `email: str`
- `password_hash: str` — empty for OAuth
- `display_name: str` — from Google profile
- `experience_level: str` — `"beginner"` | `"intermediate"` | `"advanced"`
- `confident_areas: str` — JSON array of broad topics
- `onboarding_complete: int` — 0/1
- `current_streak: int`
- `last_recommendation_id: int` — nullable FK to `recommendations.id`

### `Problem` (SQLite `problems` table)
- `id: int` — LeetCode problem ID (not auto-increment)
- `title: str`
- `difficulty: str` — `"Easy"` | `"Medium"` | `"Hard"`
- `pattern: str` — JSON array of canonical pattern IDs
- `topics: str` — comma-separated broad categories
- `test_cases: str` — JSON array (stored but not used at runtime)
- `acceptance_rate: float`
- `link: str` — LeetCode URL
- `category: str`
- `premium_only: int`

### `Submission` (SQLite `submissions` table)
- `id: int`
- `user_id: int` FK
- `problem_id: int` FK (nullable)
- `code_text: str` — stored as `"self-reported"` placeholder
- `verdict: str` — `"pass"` | `"fail"` | `"error"` | `"tle"`
- `detected_pattern: str` — the pattern the system detected
- `expected_pattern: str` — the pattern expected (from problem or ground truth)
- `target_pattern: str` — nullable, the pattern the recommendation targeted
- `gap_identified: int` — 0/1
- `diagnosis_confidence: float` — 0.0-1.0
- `topic: str` — same as `detected_pattern` in current code
- `attempt_number: int`

### `GroundTruth` (SQLite `problem_ground_truth` table)
- `problem_id: int` PK FK
- `patterns: str` — JSON array of canonical pattern names
- `confidence: str` — JSON dict mapping pattern name → float confidence

### `GapSignal` (SQLite `gap_signals` table)
- `id: int`
- `user_id: int` FK
- `pattern_id: str`
- `gap_strength: float` — 0.0-1.0
- `frequency: int`
- `last_seen: str` — ISO 8601
- UNIQUE(user_id, pattern_id)

### `Elo` (SQLite `user_pattern_elo` table)
- `id: int`
- `user_id: int` FK
- `pattern_id: str`
- `elo: float` — starts at 1200.0, min 400.0
- UNIQUE(user_id, pattern_id)

### `AnalysisResponse` (FastAPI `/analyze` output)
```python
{
    "ast": {
        "detected_patterns": [{"pattern_id": str, "confidence": float, "evidence": [...]}],
        "engine_version": "2.0.0",
        "analyzed_at": "ISO8601",
        "patterns_checked": int,
        "patterns_detected": int
    },
    "match_result": {
        "match_result": "FULL_MATCH"|"PARTIAL_MATCH"|"NO_MATCH",
        "matched_groups": [int],
        "unmatched_patterns": [str],
        "confidence_score": float,
        "reasoning_signals": [str]
    }
}
```

### `Recommendation` (two formats)

**Flask/recommender.py output:**
```python
{
    "tier": "specific"|"topic_hint"|"general_hint",
    "confidence_tier": str,
    "problem": dict|None,
    "explanation": str,
    "confidence": float,
    "topic": str,
    "pattern": str,
    "pattern_label": str,
    "difficulty": "Easy"|"Medium"|"Hard",
    "leetcode_url": str
}
```

**FastAPI/recommendation_engine.py output:**
```python
{
    "user_id": str,
    "recommended_problems": [{
        "problem_id": str,
        "target_patterns": [str],
        "reason": str,
        "difficulty_score": float,
        "expected_learning_gain": float
    }],
    "summary": {
        "primary_weak_patterns": [str],
        "focus_area": str,
        "recommendation_strategy": str
    }
}
```

---

## 15. Current Technical Debt

### Dual Backend
- Flask + FastAPI both run as separate processes on different ports.
- Core logic is duplicated: `recommender.py` vs `recommendation_engine.py`, `profile_manager.elo.py` vs `elo_engine.py`, `gap_detector.py` vs `gap_signal_engine.py`.
- Routes serve similar purposes with different auth requirements.
- **Fix:** Migrate all Flask routes to FastAPI. Unify under one process.

### Hybrid SQLite/Supabase
- `.env` contains a Supabase Postgres URL that is never used.
- All data lives in SQLite, including user profiles that have Supabase IDs.
- No migration system for schema changes.
- **Fix:** Either fully migrate to Supabase Postgres or remove the Supabase Postgres config.

### Ground Truth Not Integrated
- `problem_ground_truth` table exists, LLM client works, but no code calls `build_ground_truth()`.
- Matching Engine receives synthetic groups instead of ground truth.
- **Fix:** Seed ground truth for all problems; wire it into the analysis service.

### The `recommender.py` / `submission_handler.py` Pipeline
- `handle_submission()` always sets `gap_identified: 0`, `detected_pattern` = first pattern from problem CSV, `detected_confidence: 1.0`, `diagnosis_confidence: 1.0`.
- This means **every submission is treated as a perfect match with no gap identified**, regardless of actual code quality.
- The recommendation then operates on this always-perfect signal, making it a pure difficulty-rotation system.

### Legacy Modules
- `pathforge/ast_engine/` (extractor + classifier) is an older, separate AST system that is NOT used by the current analysis pipeline. The current pipeline uses `src/ast_detection/`.
- `pathforge/gap_detector.py` (14 lines) is a minimal gap detector that is NOT used by any current code path.
- `pathforge/judge0_client.py` is an empty file — a planned Judge0 integration that was never started.
- `pathforge/static/style.css` and `pathforge/templates/` (index.html, dashboard.html, practice.html) are legacy Flask templates not used by the Next.js frontend.

### Incomplete Elo/Gap Signal Integration
- `gap_signal_engine.py` and `elo_engine.py` are complete, tested, and have `persist_*` methods, but are never called.
- The `loader.py` service can load `user_pattern_elo` and `gap_signals`, but these tables are empty (no code writes to them).

### Frontend Gaps
- No submission form — the analysis page is read-only.
- The recommendation page shows problem list but the "Solve" button has no handler.
- `ActivityFeed` shows static placeholder text.
- No real-time data refresh after analysis.

### Auth Inconsistencies
- FastAPI `/analyze` and engine endpoints have no auth middleware (accept any user_id).
- Flask auth uses a different JWT than FastAPI auth.
- `_ensure_local_user()` creates users without seeding topic_profiles (the seed only happens in Flask register).

### Pattern CSV to DB Mismatch
- The `pattern` column in `problems` stores JSON arrays. Some problems may have patterns that don't exist in `ALL_PATTERNS`.
- `get_recommendable_patterns()` filters to only patterns that appear as the first element of any problem's pattern array. Patterns like `dp_state_machine` and `topological_sort` may have zero problems, making them permanently unrecommendable.

---

## 16. Current Roadmap

### Completed
- AST Analysis Engine with 33 detectors covering entire pattern taxonomy (`src/ast_detection/`)
- Matching Engine with confidence scoring (`src/matching_engine/`)
- Gap Signal Engine with persistence (`pathforge/gap_signal_engine.py`)
- Elo Engine with anti-drift and persistence (`pathforge/elo_engine.py`)
- New Recommendation Engine with multi-strategy support (`pathforge/recommendation_engine.py`)
- Problem bank CSV with linked patterns (`pathforge/data/pathforge_problems_fixed.csv`)
- Ground Truth LLM pipeline (`pathforge/services/ground_truth_builder.py`)
- OpenRouter integration for GPT-4o-mini (`pathforge/llm/openrouter_client.py`)
- Supabase OAuth with PKCE flow (frontend + backend)
- Next.js frontend with 5 pages (dashboard, analysis, recommendations, progress, profile)
- FastAPI engine API layer (`pathforge/api/`)
- Lightweight migration system in `db.py`

### In Progress
- None tracked. The project appears between major phases.

### Planned (from git history / file analysis)
- **Ground truth seeding**: Run `build_ground_truth()` for all CSV problems, store in DB.
- **Wiring analysis → gap → elo → recommend**: Connect the engines end-to-end so a code submission triggers the full pipeline.
- **Submission UI**: Add a form to the frontend allowing users to submit verdict after analyzing.
- **Unified backend**: Migrate Flask submission pipeline to FastAPI.

### Future Ideas (from design documents / pattern analysis)
- Judge0 integration for real code execution (empty stub exists at `pathforge/judge0_client.py`).
- SQLite → Supabase Postgres migration (connection string already in `.env`).
- Problem selector UI improvements (LeetCode link integration).
- Historical Elo charts for pattern progression.
- Session-based recommendation (warm-start after idle).
- Multi-language support (currently Python-only).

---

## 17. Common Debugging Guide

### OAuth Loops / Redirect Issues

**Symptoms:** User clicks "Sign in with Google" → browser goes to Google → redirects back to app → immediately shows login page again. No error.

**Likely causes:**
1. PKCE code verifier cookie not persisted (cross-origin redirect).
2. `detectSessionInUrl: false` in supabase client config (intentional, but may conflict with `flowType: 'pkce'`).
3. Callback page fails silently.

**Files to inspect:**
- `pathforge-frontend/src/auth/supabase.ts:16-26` — supabase client config
- `pathforge-frontend/app/auth/callback/page.tsx` — code exchange logic
- `pathforge-frontend/src/auth/authService.ts:3-15` — redirectTo URL

**Debugging strategy:**
1. Check browser's Application tab → Cookies for the Supabase auth cookie.
2. Check Network tab: after Google redirect, look for calls to `supabase.co/auth/v1/...`.
3. Add `console.log` in `AuthProvider.tsx` line 63-74 to see `onAuthStateChange` events.
4. Set `detectSessionInUrl: true` temporarily to test.

### 400 API Errors on /analyze, /gaps, /elo, /recommend

**Symptoms:** Frontend shows error toast "Request failed with status 400". Response body has `"error"` and `"stage"` fields.

**Likely causes:**
1. Invalid `user_id` (string instead of int, or non-existent user).
2. Code fails AST parsing (syntax error, banned construct).
3. Database connection issue (SQLite locked).

**Files to inspect:**
- `pathforge/api/services/analysis.py` — error stages: "VALIDATION", "AST", "MATCHING"
- `pathforge/api/services/gap.py` — error stage: "GAP"
- `pathforge/api/services/elo.py` — error stage: "ELO"
- `pathforge/api/services/recommend_service.py` — error stage: "RECOMMENDATION"

**Debugging strategy:**
1. Check the `"stage"` field in the error response to identify the failing component.
2. For "AST" errors: test the code snippet directly with `ast.parse()`.
3. For database errors: check SQLite file permissions, WAL mode locks.
4. For "RECOMMENDATION" errors: check `user_pattern_elo` and `gap_signals` table state.

### CORS Errors

**Symptoms:** Browser console shows CORS policy errors. Frontend can't reach backend.

**Likely causes:**
1. Backend running on different port than frontend expects.
2. CORS origin mismatch.

**Files to inspect:**
- `pathforge/api/app.py:22-27` — FastAPI CORS config
- `pathforge/app.py:18-24` — Flask CORS config
- `pathforge-frontend/src/services/api/client.ts:1` — `API_BASE` URL

**Debugging strategy:**
1. Verify `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).
2. Verify backend is running on port 8000.
3. Check that `allow_origins` includes the frontend origin.

### Missing Migrations

**Symptoms:** Code references a column or table that doesn't exist. SQLite errors in logs.

**Likely causes:**
1. Old database file from a previous version.
2. `_apply_lightweight_migrations()` missed a column.

**Files to inspect:**
- `pathforge/db/db.py:102-137` — `_apply_lightweight_migrations()`
- `pathforge/db/schema.sql` — full schema

**Debugging strategy:**
1. Delete `pathforge.db` and restart (will be recreated fresh).
2. Check `PRAGMA table_info(table_name)` for missing columns.
3. Add a new migration in `_apply_lightweight_migrations()`.

### Ground Truth Mismatch

**Symptoms:** Analysis shows wrong patterns for a known problem. Match engine gives unexpected results.

**Likely causes:**
1. `problem_ground_truth` table is empty.
2. Analysis service uses synthetic groups instead of ground truth.

**Files to inspect:**
- `pathforge/api/services/analysis.py:39-46` — synthetic group creation
- `pathforge/services/ground_truth_builder.py` — LLM pipeline

**Debugging strategy:**
1. Check `SELECT * FROM problem_ground_truth LIMIT 5`.
2. If empty: the ground truth pipeline has never been run.
3. If populated: analysis service doesn't query it — it uses `ast_for_matching` as both source and expected.

### Recommendation Bugs

**Symptoms:** Recommendations don't make sense. Always same pattern. No recommendations.

**Likely causes:**
1. `recommender.py` — topic rotation always picks same fallback.
2. `recommendation_engine.py` — `user_pattern_elo` table is empty (all Elos at default 1200).
3. `get_weakest_topics()` returns empty because recommendable patterns set is empty.

**Files to inspect:**
- `pathforge/routes/profile.py:206-236` — `_active_recommendation()`
- `pathforge/recommender.py:126-147` — `_select_problem()` SQL
- `pathforge/db/profile_manager.py:270-321` — `get_weakest_topics()`
- `pathforge/db/profile_manager.py:177-190` — `get_recommendable_patterns()`

**Debugging strategy:**
1. Check `SELECT topic, elo_rating FROM topic_profiles WHERE user_id = ? ORDER BY elo_rating ASC`.
2. Check `SELECT DISTINCT json_extract(pattern, '$[0]') FROM problems` — if certain patterns are missing, they're not recommendable.
3. For the new engine: check `SELECT * FROM user_pattern_elo WHERE user_id = ?` — if empty, no Elo data exists.

### Frontend State Issues

**Symptoms:** User sees stale data. "No recommendations yet" after submitting. Auth state flashes.

**Likely causes:**
1. `useApiData` doesn't re-fetch after mutations.
2. `_accessToken` module variable lost on navigation.
3. AuthProvider loading state race condition.

**Files to inspect:**
- `pathforge-frontend/src/hooks/useApi.ts` — `useApiData` refresh logic
- `pathforge-frontend/src/services/api/client.ts:3-7` — `_accessToken` lifecycle
- `pathforge-frontend/src/auth/AuthProvider.tsx:52-77` — session loading

**Debugging strategy:**
1. Check Network tab for API calls on page load.
2. Check if `Authorization` header is present in API requests.
3. Call `.refresh()` from the exposed hook after submission.

---

## 18. Design Decisions

### AST Instead of LLM Runtime Analysis

**Decision:** Use static AST analysis (Python `ast` module) instead of sending code to an LLM for runtime analysis.

**Why:**
- Deterministic: same code → same result every time.
- No API cost: 33 detectors run in <50ms locally.
- No latency: analysis completes in the same HTTP request.
- No prompt brittleness: LLM classification of code patterns is unreliable and expensive.
- Privacy: user code never leaves the server.

**Trade-off:** Cannot detect patterns that require runtime information (e.g., actual data flow, time complexity). But for algorithmic pattern detection, AST structure is sufficient.

### Ground Truth Caching (Stored, Not Used Yet)

**Decision:** Generate problem ground truth once via LLM, store in SQLite, reuse indefinitely.

**Why:**
- Avoids LLM API cost per analysis.
- Ensures consistent expected patterns across all users.
- Enables offline labeling of the problem bank.

**Trade-off:** Ground truth is static; if the LLM mislabels a problem, all analyses for that problem are wrong until the ground truth is updated.

### Problem-First Analysis

**Decision:** The analysis pipeline treats the problem (identified by `problem_id`) as the primary context. Expected patterns come from the problem's ground truth.

**Why:**
- Aligns with how users think ("I'm solving Two Sum" → "expected pattern: hash_map_lookup").
- Enables per-problem learning: gap signals are meaningful only relative to what the problem actually tests.

**Current status:** Not fully implemented. The analysis service ignores `problem_id` entirely and creates synthetic expected groups.

### Supabase Authentication

**Decision:** Use Supabase Auth (Google OAuth + PKCE) instead of a custom auth system.

**Why:**
- Eliminates password management, hashing, reset flows.
- Provides JWKS for stateless token verification.
- Scales to arbitrary user count without DB changes.
- PKCE flow works without client secrets (safe for Next.js).

**Trade-off:** Dependency on Supabase availability. OAuth adds redirect complexity. Local development requires a Supabase project.

### Two Recommendation Engines

**Decision:** Build a new recommendation engine (`recommendation_engine.py`) alongside the legacy one (`recommender.py`).

**Why:** The legacy engine is tightly coupled to Flask, `topic_profiles` table, and the manual submission pipeline. The new engine is stateless (operates on loaded data) and can work with the FastAPI layer without touching legacy code.

**Trade-off:** Duplicated logic. Two engines to maintain. Different Elo scales (800 vs 1200 starting). The new engine lacks the topic rotation and diversity logic of the legacy engine.

### Flat 33-Pattern Taxonomy

**Decision:** Use 33 canonical algorithmic patterns in a flat taxonomy with no hierarchy or prerequisites.

**Why:**
- Covers ≥95% of LeetCode-style problems.
- Flat taxonomy simplifies detection (no hierarchy resolution needed).
- Each pattern maps to a single detector, which maps to a single Elo rating.
- Easy to extend (add a new pattern = add a new detector).

**Trade-off:** No concept of prerequisite relationships (must know "binary search" before "binary search on answer"). No concept of pattern families for transfer learning.

---

## 19. Things Future LLMs Must Know

### Current Assumptions

1. **SQLite is the single source of truth** for all application data. The Supabase Postgres URL in `.env` is unused.
2. **Supabase Auth is the only active auth path.** Flask JWT auth exists but is not called by the frontend.
3. **The analysis pipeline (`/analyze`) does NOT authenticate the user.** The `user_id` field is accepted as-is.
4. **The matching engine compares patterns against themselves** (synthetic groups). Ground truth table is empty.
5. **Submissions always report perfect matching.** `handle_submission()` hardcodes `detected_confidence: 1.0`, `gap_identified: 0`, `diagnosis_confidence: 1.0`.
6. **The `user_pattern_elo` and `gap_signals` tables are always empty** in practice — no code writes to them.
7. **Topic profiles (`topic_profiles.elo_rating`) are the de facto skill model**, despite `user_pattern_elo` existing.
8. **The codebase is Python 3.10+** (uses `str | None` syntax, `list[str]` type hints).

### Do NOT Change (Architectural Invariants)

1. **Detectors must remain stateless and isolated.** No detector should call another detector, modify shared state, or perform I/O.
2. **The AST parser must always sanitize code** before parsing. The `sanitize_code()` function in `parser.py` is the security boundary.
3. **The 33-pattern taxonomy (`ALL_PATTERNS` in `patterns.py`) is the single source of truth** for pattern names. All code should reference constants, not string literals.
4. **The schema in `schema.sql` must remain backward-compatible.** New columns should be added via `_apply_lightweight_migrations()`, not by rewriting `CREATE TABLE`.
5. **The submission pipeline must remain atomic.** `pipeline.py` commits only once at the end of the pipeline.
6. **The FastAPI and Flask apps must not share in-memory state.** They can share the same SQLite file but not Python objects.

### Modules That Should Never Be Casually Rewritten

| Module | Reason |
|--------|--------|
| `src/ast_detection/detectors/*.py` | 33 hand-tuned detectors with evidence scoring. Each represents months of iteration. |
| `src/ast_detection/parser.py` | Contains the security sanitizer. Mistakes here allow code injection. |
| `src/matching_engine/matching_engine.py` | The algorithm for group match confidence is carefully designed. |
| `pathforge/db/db.py` | The migration system (`_apply_lightweight_migrations()`) is fragile. Wrong ordering breaks DB. |
| `pathforge/auth/auth_middleware.py` | JWT verification is security-critical. The JWKS fetching + caching logic must be correct. |

### Current Active Refactors

- None explicitly tracked. The repository appears mid-transition between the Flask + legacy engine era and the FastAPI + new engine era.

### Known Unfinished Features

1. **End-to-end engine pipeline**: `/analyze` → AST → Match → Gap → Elo → Recommend → Persist.
2. **Ground truth seeding**: Run `build_ground_truth()` against the full problem bank.
3. **Frontend submission form**: Wire up `POST /api/submit` (or a FastAPI equivalent).
4. **Engine auth**: Add `get_current_user` dependency to `/analyze`, `/gaps`, `/elo`, `/recommend`.
5. **Single backend**: Migrate Flask routes to FastAPI, remove `pathforge/app.py`, `pathforge/routes/`, `pathforge/static/`, `pathforge/templates/`.
6. **Judge0 integration**: Empty stub at `pathforge/judge0_client.py` — planned but not started.
7. **Historical Elo charts**: Frontend `ProgressView` shows current Elo but not history over time.
8. **Pattern unlock/dependency system**: No mechanism ensures a user has mastered prerequisite patterns before advancing.
9. **Multi-language support**: Only Python is supported. The AST engine is Python-specific.
