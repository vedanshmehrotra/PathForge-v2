# Foundation acceptance contract

## Scope of this batch

Keep pattern overlap, canonical strategy selection and authority/product effects
separate. The approved comparison safeguard restricts skill updates without
changing scoring formulas, canonical authority, feature defaults or recommendation
policy. Related representation and detector work is specified separately in the
descriptive-approach and evidence-qualification contracts.

`SolutionApproach.pattern_evidence_state` is additive and observational:

| State | Meaning | Display consequence |
| --- | --- | --- |
| `NOT_EVALUATED` | Preparation metadata only; code not compared | No alignment claim |
| `ALL_OBSERVED` | All listed components match under the existing matcher | An explicit unreviewed proposal can show listed-pattern overlap, with a tentative label |
| `SOME_OBSERVED` | Existing matcher reports partial component overlap | Keep combined requirements; no complete-approach claim |
| `NONE_OBSERVED` | No listed component observed | Inconclusive; coverage or expectations may be unsuitable |
| `UNAVAILABLE` | Ambiguous relationships, conflicting authority, vocabulary gaps, or inconsistent representation | Preserve diagnostic rows; no usable approach-alignment claim |

The state does not validate the algorithmic suitability or completeness of the
stored proposal. It does not select a strategy, confer authority, change scoring,
or establish functional correctness. Explicit `ONE_OF` siblings remain options;
proposed alternatives are not represented as verified universal requirements.
Old payloads without the new field cannot acquire proposed-alignment claims.

## Skill consequences: approved comparison safeguard

| Comparison | Skill behavior |
| --- | --- |
| Missing, partial, unmatched, ambiguous, unsupported or conflicting comparison | Practice/submission and streak only; no profile, Elo, gap or skill-based recommendation update |
| Complete overlap with unreviewed/LLM-proposed expectations | Same practice-only behavior, including no positive Elo update |
| Complete, explicit, usable comparison with authorizing metadata | May update skills only if the existing legacy evidence gate also permits it |
| B6 on | The existing canonical gate must additionally permit updates; it cannot bypass either preceding gate |

The user approved skipping **all** skill updates for inconclusive/unsupported
comparisons, including positive updates. Shared approach qualification keeps
this check consistent with the comparison metadata; persistence verifies actual
overlap with the existing matcher. The first matched group's authority is used,
as in legacy persistence, never an unmatched alternative's authority.

Canonical Shadow remains a separate observational strategy result with B6 off;
canonical abstention does not rewrite an otherwise authorized pattern comparison.
The safeguard grants no new authority and leaves the legacy gate, B6 decisions,
scoring formulas and default flag unchanged. Stored `verdict_type` and legacy
comparison fields remain historical diagnostics, not proof of scoring eligibility.
`persisted.skill_updates_skipped` reports the combined gates' actual effect.
Existing skill rows and historical submissions are not rewritten or recomputed.

## Repeatable isolated checks

From the repository root, using an installed backend environment:

```powershell
python -B scripts/verify_foundation.py --output C:/path/to/external/evidence
```

This blocks database/network access before imports, freezes source/expectation
fixtures, executes real builder, cached resolver, analysis, matching, persistence,
Shadow and API paths with connection doubles, checks practice-service scenarios,
then runs an explicit isolated pytest allowlist. Sources are parsed, never run.
There are no external LLM calls. The metadata/expectations are synthetic, not
copies of production ground truth. Repeated identifiers/names are implementation
variants, not independent problems. The frozen matrix is development acceptance
evidence; it is not an independent statistical holdout for cumulative detector work.

Detector coverage gaps are reported separately from the acceptance-suite result.
The command fails on targeted negative false detections, unsafe canonical
conclusions, protected-state changes or regression failures. A green exit does
not mean all algorithm families are supported, all detections are correct, or a
learner's code is functionally correct. Off-target detections and uncertain
canonical eligibility require source review; the summary is not a full confusion
matrix or a statistical accuracy claim.

Frontend checks use the existing installed Vitest and Next.js/TypeScript tools.
No new dependency or CI provider is required by this batch.

For the checked-in Playwright CLI suite:

1. Build/start **only** the frontend on `127.0.0.1:3111` with process overrides
   `NEXT_PUBLIC_API_URL=http://127.0.0.1:49999`,
   `NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:49998`, and a dummy anon key.
   Do not reuse a live-auth session or production endpoint.
2. Serve the external evidence directory on `127.0.0.1:3112` with Python's static
   HTTP server. It contains synthetic data; never serve a credentials directory.
3. In that external directory, open an isolated Chrome CLI session and run
   `scripts/browser/foundation-smoke.js` through `playwright-cli run-code`.
4. Close only the sessions started for the checks.

For production-build checks, build with those same overrides before `next start`;
public values are embedded at build time. The suite explicitly stubs the local
Vercel analytics script, which is normally injected by Vercel hosting.

The browser suite exercises prepare/run/edit flows for actual engine payloads,
comparison presentation, skipped consequences, mobile layout and actual-service
practice filtering/skip/reset. Auth and API transport are mocked. This is not
live backend/database, analytics or OAuth verification; production writes are
outside scope. Desktop heading styles, console/page errors and failed requests
are checked alongside the visible comparison outcomes.

`verify_foundation.py` also exports `approach-contract.json` from actual local
builder/resolver/analysis/persistence execution. Under the same isolated setup,
run `scripts/browser/approach-contract-smoke.js` through Playwright CLI to check
descriptive-only, mixed and supported approaches, explicit code-only opt-in,
retained source, mobile layout and delayed errors from a previous problem.
HTTP 409 responses in those deliberately unsupported flows are expected and
reported separately from unexpected console/network failures.

## Cached correction: design boundary, not an implemented endpoint

Ordinary `/analyze` remains DB-only. Ordinary `/prepare-problem` still preserves
existing rows. No refresh/migration is implemented here.

An [offline correction package tool](GROUND_TRUTH_CORRECTION.md) now prepares a
proposed replacement using the real builder, retaining the supplied historical
snapshot and fingerprints. It cannot fetch, generate, apply or activate a row.

Before implementing explicit correction, inspect the target schema read-only
under separate authorization. A correction must retain the full previous
artifact and record source fingerprint, model/request settings, prompt/contract
version, generation time and correction reason. Historical metadata that was not
recorded must be marked unknown, not reconstructed as fact.

An append-only version record and an atomic switch to a validated candidate are
the proposed persistence contract. Replacing a row must never inherit a previous
version's external/human authority: a generated replacement remains proposed.
The exact storage/migration and concurrency protection need review before code
or shared-state changes. No automatic regeneration, blanket backfill or authority
promotion follows from this document.

## Recommendation boundary

The runtime history-based policy remains independent of detector/ground-truth/
skill conclusions. Local tests qualify exposure, difficulty, exclusions, aliases,
repeat submissions and empty/error states. They do not establish user satisfaction,
retention improvement or optimal recommendation quality. Such claims need later
evaluation with independently consented user evidence.
