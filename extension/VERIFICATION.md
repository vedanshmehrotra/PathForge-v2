# Extension verification — 20 October 2026

Version **0.4.1** adds accepted-submission scoring safeguards, rating-derived levels,
and brief XP feedback. Elo calculations and evidence/authority gates are preserved.

## Executed checks

**68 browser checks passed** with the actual MV3 extension loaded in an isolated Chromium profile. The tests used Chrome storage, tabs, script injection, and service-worker APIs directly. LeetCode editor/submission data and authenticated PathForge responses were controlled fixtures, not real user submissions.

The suite covers:

- Empty-starter monitoring, draft typing and Run/Test without scoring, automatic rejected-to-accepted recovery, idle submission deduplication, active-source-only polling, and accepted solutions with an unrecognized approach.

- Fresh XP feedback, level-boundary transitions, fade-out, no reward replay from cache or a duplicate server receipt, and unchanged XP explanations.
- Completed-submission identity, automatic completion detection without an editor change, draft-only recording, and refusing automatic writes to an older backend.

- One-time setup, hidden account controls after connection, remembered reconnection, and account verification.
- Complete Monaco-model capture including offscreen code; a React-held editor ref when the global Monaco API is absent.
- An explicitly opened submission as the full-code fallback. A normal problem page never silently substitutes an old submission for an unreadable editor.
- URL subroutes, automatic problem preparation, exact source preservation, verified backend user ID, and Python-only validation.
- Empty starter code/docstrings, valid single-line Python implementations, and refusal to scrape partial visible lines.
- LeetCode verdict matching by problem, language, and source. Old accepted code and another problem's result are rejected.
- Existing pattern-focused recommendations after a matching failed submission; the existing calendar-practice policy otherwise.
- Three clickable suggestions, related follow-up ordering, backend target-pattern labels, topic labels where no pattern is supplied, safe URLs, and escaped text.
- No progress-dashboard API requests or developer metrics in the compact panel.
- Cache reuse when rechecking/reopening identical code, stale-result invalidation after edits, and code changes during preparation.
- Explicit code-only fallback for unsupported comparison; independent recommendation failure/retry.
- Pending/uncertain write protection, deliberate retry, disconnect cleanup, and rejection of late account responses.
- No horizontal overflow at 280, 320, 360, and 440 pixels; compact vertical layout; reduced-motion support; no uncaught runtime errors.

Screenshots of the final connected layout were generated at all four widths and visually inspected. The test data is synthetic. Tests and browser profiles are excluded from the extension package.

Run `scripts/verify_extension.ps1` with an existing Playwright CLI/Chromium installation. The report and screenshots are saved in `.playwright-cli/extension-review/`. `scripts/verify_extension_browser.js` contains the executable checks.

JavaScript syntax, manifest JSON/assets, and extension-package contents were also checked.

## Live-site limit

Opening the real LeetCode Two Sum page in the isolated automated browser returned **HTTP 403 / an access challenge**. The challenge was not bypassed. Consequently, current code extraction and submission-result reads against the user's actual LeetCode session remain **unverified**. Monaco/React and submission fixtures demonstrate the implemented behavior but do not establish compatibility with every live LeetCode build.

The previous version's live API health/schema checks do not establish that this new automatic workflow has saved a real account submission. No production-authenticated analysis, paid preparation call, real Google sign-in, or actual LeetCode submission was performed in this review.

After reloading the extension in Chrome, the remaining live check is to open an existing Python solution in LeetCode and open PathForge. Confirm that it reads the correct problem/code, records analysis in the same account, and labels correctness only when a matching LeetCode submission is available.

## Behavioral boundaries

- Pattern detection does not verify correctness or optimality. Only a matching LeetCode submission supplies a verdict.
- A catalog topic is not relabeled as a verified algorithm/pattern requirement. Recommendation bubbles distinguish the API's target pattern from its catalog topic.
- The extension chooses existing recommendation modes; it does not duplicate or replace their algorithms or store LeetCode verdicts as backend skill authority.
- Confirmed recent results are cached for the browser session. An uncertain write is never automatically repeated.
- This remains a Chrome 116+ package. Zen/Firefox support is not implemented.
