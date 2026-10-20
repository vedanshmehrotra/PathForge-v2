# Preparation and practice recovery

20 October 2026. Addresses the real preparation report and the recommendation audit; no detector, scoring, authority or stored-ground-truth rewrite.

## Preparation

New generation uses wire contract `approach_contract_version: 3`: a nonempty list of explicit approaches, each owning its patterns and confidence. No redundant top-level patterns/confidence are allowed. The builder validates every approach, derives the legacy union locally, and persists the existing structured format as `llm_proposed`. Conjunctive components, explicit alternatives and unsupported descriptions retain their established meaning. Existing v1/v2 generation inputs remain accepted under their existing strict checks. Existing cached rows are never regenerated automatically.

Invalid output and truncated completions are rejected before ground-truth writes. Repeating invalid paid completions is not a repair mechanism. Transient connection/408/5xx failures keep the existing bounded transport retries; authentication failures and 429 do not auto-retry. Typed, sanitized failures distinguish invalid output, provider unavailability, rate limits and source lookup failures. Preparation retains HTTP 502 for provider/transport failures, 404 for missing problems, and existing structured 409 readiness responses. Numeric provider Retry-After values are exposed when available. Pasted source remains editable and can explicitly continue as code-only inspection. No rating eligibility follows from this fallback.

## Practice

Practice mode remains separate from diagnostic and skill state. Defaults/legacy policies are preserved. Calendar policy reads distinct latest linked problems, catalog metadata and code-only counts for the verified user. An incomplete account load is an error with account retry, never an empty bank. Account/recommendation requests have a 20-second client timeout; preparation has a 120-second client timeout. There are no automatic frontend retries.

Recognized algorithm tags can justify factual related-topic links. Shared Math, Hash Table, Simulation, Design or unknown tags alone cannot. This supports approximate problem relatedness, not inferred intended approaches or remedial diagnoses. Default choices do not exceed the latest dated difficulty (Easy without usable context); explicit difficulty filters remain available. At most one previously attempted problem is offered, labeled as a revisit. Every valid dated problem has the same seven-day eligibility interval, including the latest one.

Skips are account-scoped browser preferences, shared by the dashboard and recommendation page, with a 30-day expiry, explicit reset and a 50-active limit. Blocked storage falls back to tab memory with an accurate notice. They are not cross-device preferences, success labels or evidence of learning. Dashboard preserves all three offered options. Empty-state classification distinguishes skipped eligible choices, cooldown restrictions, missing candidates and default difficulty limits.

## References and limits

- [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs): schema support varies by model/provider. Shape guarantees alone do not prove semantic agreement across duplicated fields. This change avoids that duplication and retains local validation without requiring a new model or provider capability.
- [PostgreSQL SELECT](https://www.postgresql.org/docs/current/sql-select.html): ordered `DISTINCT ON` selects the latest per-problem row before the bounded outer query. Text timestamps are not cast in SQL; malformed dates remain safe unknowns.
- [NN/g error-message guidelines](https://www.nngroup.com/articles/error-message-guidelines/): identify the actual failure and provide an actionable recovery without blaming the user's input for a provider error.

No runtime LLM is added to recommendations. No database migration, submission execution, catalog ingestion service or mandatory human review is introduced. Missing/incorrect catalog metadata, unknown external accepted history, cross-device skip syncing, learning-outcome signals, independently measured educational relevance and live provider quality remain separate limitations. Paid flags are only as accurate as stored metadata. Development/browser fixtures do not establish production prevalence or ground-truth correctness.
