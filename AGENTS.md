# PathForge — Development Rules

## Working Practices
- Inspect relevant source, configuration, callers, and tests before modifying anything. Trace actual behavior instead of inferring architecture from filenames.
- Treat documentation and historical reports as context; when they disagree with code, identify the discrepancy rather than assuming the documented behavior exists.
- Make focused changes using existing conventions and utilities. Prefer simple solutions; do not rewrite working AST, Matching, Gap, Elo, or Recommendation engines or introduce unnecessary dependencies.
- Preserve unrelated and uncommitted work. Do not create commits or branches unless requested; do not reset, discard changes, force-push, delete branches, or rewrite history without explicit authorization.

## Application Boundaries
- The active backend is `pathforge.api.app:app`; the Next.js frontend calls it directly. Legacy Flask routes, templates, authentication, and submission behavior are separate and must not be treated as the active API.
- The shared database layer uses PostgreSQL through `DATABASE_URL`; its `db_path` argument does not provide SQLite isolation. Inspect the relevant schema and SQL before changing persistence.
- Preserve API contracts and authenticated-user ownership. Do not trust a request's `user_id` in place of the verified identity or weaken authentication to make tests pass.
- Backend confidence values use 0–1. Convert to percentages only for display; compare thresholds against normalized values and respect the Meter's 0–100 scale.

## Problem Preparation and Ground Truth
- Keep GraphQL fetching and ground-truth generation behind ProblemResolver. Do not add external calls to analysis or scoring engines.
- DB-only `/analyze` and cache-building `/prepare-problem` remain the intended boundary. Inspect actual callers and cache-miss behavior; do not assume that separation is already enforced.
- Do not automatically regenerate existing ground truth. Explicit corrections must retain provenance and versioning; never relabel ground truth merely to improve evaluation metrics.
- Preparation transport/LLM failures should return HTTP 502 with a useful message; missing problems map to 404. Do not cache empty or invalid ground truth as successful preparation.

## Shadow Safety and Authority
- Treat Shadow analysis as observational unless the task explicitly authorizes product consequences. Keep product gating disabled by default; do not silently promote Shadow results or change Elo, gaps, profiles, or recommendations.
- Preserve the B1–B11 boundaries: observations, techniques, and strategies have distinct roles; detection, family coverage, primary selection, authority, and product eligibility are separate decisions.
- Only conclusion-eligible strategies may be primary conclusions. Prefer `UNRESOLVED` when evidence is insufficient; absence of evidence is not contradiction, and `PROVISIONAL` is not confirmation.
- Canonical product authority requires `HUMAN_APPROVED` or `EXTERNAL_VERIFIED`. Structural observation, LLM inference, specificity eligibility, or favorable parity metrics do not confer authority. Preserve explicit `ONE_OF` semantics and fail closed on unknown/conflicting authority.
- B10/B11 evaluation and specificity findings do not authorize strategy promotion. Preserve legacy comparison data and keep Shadow failures from breaking production analysis.

## Validation
- Run focused tests for the changed behavior first, then broader regression checks when warranted. Investigate test assumptions and weak assertions rather than treating a pass as proof of correctness.
- Distinguish unit, database/API integration, corpus evaluation, and browser tests. In-process scripts named E2E do not verify browser workflows.
- Once Playwright is configured, use it for real user-facing verification: authentication, navigation, API interactions, visible outcomes, and resulting data where appropriate.
- Report only checks actually executed, separating passed, failed, and unexecuted checks. Never claim deployments, browser flows, or historical test results were verified in the current task without executing them.

## Database, Deployment, and Secrets
- Inspect environment targets and side effects before importing the API, running integration tests, migrations, seeders, or evaluation scripts. API import initializes the database; some tests delete fixed user IDs in the configured database.
- Use isolated test databases and test accounts. Do not casually run destructive operations against shared or production state; destructive actions require explicit authorization for the specific target and operation.
- Inspect frontend/backend/auth/database configuration before deployment changes. Do not assume branch deployments or external Render/Vercel settings match production or repository documentation.
- Never commit secrets or expose credentials, tokens, OAuth codes, private keys, or connection strings in logs, test output, or documentation. Preserve existing secret management and environment protections.

## graphify

- Graphify is optional local tooling. Use it when complex architecture or cross-file relationships benefit from graph navigation; choose direct source inspection for routine tasks.
- When explicitly requested with `$graphify` or `/graphify`, follow the available skill instructions.
- Check the graph's scope and freshness, distinguish extracted relationships from inferred ones, and verify important conclusions against source. A graph scoped to `pathforge/` does not cover the frontend or `src/`.
- Refresh the relevant graph only when needed for the task. Graph generation and updates are not required after every code change.
- Keep generated `graphify-out/` output local and ignored. Its absence must not block repository work.

## Response Style

- Keep user-facing responses concise and execution-focused.
- Do not provide essays, tutorials, or unnecessary explanations unless requested.
- Before making changes, briefly state the intended action when useful.
- After execution, report only:
  1. what changed,
  2. verification performed,
  3. any important issue/blocker.
- Prefer short bullets over prose.
- Do not repeat the user's request or explain obvious implementation details.
- Keep code quality, testing, and correctness unchanged; brevity applies to communication, not implementation.
