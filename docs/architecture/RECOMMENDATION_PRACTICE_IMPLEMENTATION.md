# Recorded-practice recommendations

Local implementation contract. Deployment, shared database access and migrations
remain separately authorized operations.

This document describes `recorded_practice_v1`, preserved for API compatibility.
The frontend now explicitly requests the additive `calendar_practice_v2` policy;
see [Calendar-aware practice POC](CALENDAR_PRACTICE_POC.md) for its dated return,
follow-up, general-choice and evidence limitations. Neither policy infers skills.

## User experience

The normal mixed/daily-problem workflow needs no topic selection. After a user
records a problem through analysis, suggestions can change using that exposure.
Difficulty is an optional filter across the bank, not a prerequisite. Skipping
is a page-session choice, reset on navigation/account changes, not a completion.
Opening LeetCode does not prepare, analyze, score or mark a problem complete.

## Runtime contract

- The existing authenticated `/recommend` endpoint accepts `mode: practice`.
  Omitted mode preserves the legacy API; dashboard and recommendations explicitly
  request practice mode. Identity comes from verified auth, not request user_id.
- `pathforge/practice_recommendations.py` is a pure deterministic policy. It uses
  safe stored problem links, titles, difficulty, descriptive source-topic tags
  and the latest 1,000 problem-linked submission records, newest database ID first.
  One extra row detects truncation. Responses disclose bounded/unmapped history.
- Internal database IDs stay internal. URL aliases share exposure/skip identity;
  conflicting IDs and unusable destinations/metadata are excluded conservatively.
- Repeated analyses of a problem count once within the history window. Prefer
  problems outside that window, balancing listed topic exposure and list variety.
  Ties prefer easier source difficulty, then stable internal identity.
- When available, include one older recorded problem after two new choices.
  Fill remaining space from older revisits if new choices run out. Withhold the
  latest recorded problem to avoid immediately reassigning the same submission.
  This is a choice heuristic, not a validated spaced-repetition schedule.
- Explanations describe recorded exposure, never solved/mastered/weak labels.
  Technique detections, ground truth, Shadow, authority, pass/fail verdicts, gaps
  and Elo do not enter this policy. No inferred learner-state writes occur.
- New responses identify `recorded_practice_v1`, recommendation kind and explicit
  available/no_candidates/session_exhausted/caught_up states. Compatibility fields
  remain; pattern is empty and score is null because neither is inferred.
- Difficulty/exclusions apply before selection. No hidden fallback changes the
  user's filter. Failed history reads remain errors, not a fabricated cold start.
- The frontend ignores legacy weakness explanations, labels topics as catalog
  metadata, and hides stale account/filter responses while fetching new choices.

## Limits and verification

The bank is existing application data, not an independently verified solution
catalog. Topic tags can be missing/wrong; they describe suggestions rather than
proving requirements. No manual per-problem approval is required for suggestions.
Unknown history is not assigned a topic. Old submissions outside the bounded
window may be suggested again. No LeetCode account history or judge is integrated.

The eight-item source-checked experiment remains an isolated preference prototype;
it is not the runtime catalog and is not imported by production code. The former
preference-only integration proposal is superseded by this history-based contract.

Use isolated connection doubles to test actual service/route wiring, ownership,
no writes/diagnostic loaders, duplicates, aliases, history limits and empty/error
states. Verify real service-produced responses through local browser transport
mocks, optional filters, skip/reset, navigation and retry. Such checks establish
local behavior, not live database coverage, user satisfaction or learning benefit.
