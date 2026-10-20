# Practice records and pattern levels

Saved practice and skill scoring have separate purposes. `GET /auth/profile`
returns `practice_records` from the observed patterns in saved analyses,
including comparisons that are ineligible for scoring. Secondary detected
patterns are included. One problem counts as one practice session per UTC date
for each observed pattern. Existing `profiles` retain their scoring semantics.
The reader handles both PostgreSQL's decoded JSONB arrays and legacy JSON text.
Native database timestamps and legacy ISO text are normalized to UTC before
counting sessions or comparing recency; no database column conversion is needed.

The website refreshes practice records and ratings on focus and every 30 seconds
while visible. An old scoring-profile timestamp no longer hides recent practice.

## Repeated analyses

`/analyze` takes an optional `practice_event` with `source: "extension"` and a
LeetCode `submission_id` and `submission_status` (`accepted` or `failed`).
The companion supplies the ID only after comparing the
complete captured code with a completed LeetCode submission. Its editor monitor
checks for newly completed submissions without requiring a tab reload, including
when the panel was opened on untouched starter code. It polls the active source
tab at most every ten seconds. Inactive source tabs are not polled.

Opening the panel on nonempty code or pressing Recheck can analyze a draft for
pattern feedback. Typing invalidates stale results without starting an analysis
for each edit. Run/Test results do not qualify for Elo. Completed accepted and
rejected submissions are analyzed automatically when their data can be read.

The server serializes each user's persistence transaction with a PostgreSQL
advisory transaction lock. A unique `(user_id, analysis_key)` index prevents
duplicate recording. Replaying the same LeetCode submission returns its existing
receipt with no repeated Elo, profile, gap, streak, or recommendation effects.
Website analyses and unsubmitted extension drafts use a code fingerprint and UTC
date, so an explicit practice revisit on a later day can be recorded again.

Extension drafts, rejected submissions, and submissions with an unconfirmed
verdict cannot score or consume the daily scoring allowance. An accepted
correction is eligible later the same day, subject to the existing pattern
comparison and authority rules. An accepted but unrecognized alternative stays
Accepted and receives no automatic skill penalty. A different submitted solution
can still be saved, but a problem can affect scoring at most once per user per
UTC day. These are
additional restrictions on the existing comparison/authority gates. They never
grant authority to proposed approaches or observational patterns, and they do
not change the Elo calculation or verify LeetCode account ownership.

`persisted.replayed`, `persisted.skill_updates_skipped`, and
`persisted.score_reason` explain the result. Submission metadata is retained in
`submissions.practice_event` for traceability; it never grants pattern authority.
Recognizable legacy extension origins without this metadata are restricted to
draft analysis. All extension clients should be updated to the current release.

`practice_policy_version: 2` on
`GET /auth/session` tells the companion that these safeguards are available.
Version 0.4.1 does not submit automatic analyses to a backend with an older policy.

## Levels

Levels display the existing per-pattern Elo from `user_pattern_elo`. They are not
a second scoring or cumulative-XP system:

* Experience = max(0, current Elo - 400).
* Each level spans 200 XP. Level = floor(experience / 200) + 1.
* Progress is the experience remaining within the current level.

For example, 1,232 Elo displays level 5 with 32 / 200 XP. Existing ratings carry
over; XP and levels can fall when a rating falls. Topics with practice but no
rating show their practice record without inventing a level.

`POST /elo` returns `pattern_levels`. Fresh `/analyze` Elo updates include
`level_before` and `level_after`, computed by the same backend helper. The
companion animates only a newly confirmed rating change, then hides the feedback.
Cached and replayed results do not repeat it. Reduced-motion preferences apply.

## Release order

Deploy the API first: normal startup applies the additive `analysis_key` and
`skill_updates_applied` and `practice_event` columns and their indexes from
`schema_pg.sql`. Deploy
the website, then reload/install the 0.4.1 extension. No historical ratings are
recomputed. Recent saved practice is read from existing submission records.

The isolated PostgreSQL tests in `pathforge/tests/test_practice_tracking_postgres.py`
cover simultaneous identical submissions, simultaneous different submissions on
the same problem/day, and native JSONB recency. They require an explicitly supplied
`PATHFORGE_TEST_DATABASE_URL` pointing to a dedicated test database. They never
fall back to the application's `DATABASE_URL`. Each test creates and cleans up
its own schema. Run them before release to verify concurrency and native JSONB
behavior against PostgreSQL. Apply the schema migrations to a dedicated test
database separately before release; skipped tests are not integration evidence.
