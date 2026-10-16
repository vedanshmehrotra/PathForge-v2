# Guided-practice prototype

Isolated research code; not imported by FastAPI or the frontend. The existing
recommendation policy remains the default. No database, ground-truth, detector,
Elo, gap, Shadow, LLM or submitted-code execution is used.

Run from the repository root:

```powershell
python -B -m experiments.recommendations.practice_policy --topic Strings --difficulty Easy
```

The eight-item catalog records official problem-page URLs as provenance, with
identity/title/difficulty checked on 2026-10-16. Broad topic choices are editorial
practice categories, not complete strategy definitions or approved ground truth.
The catalog deliberately contains no Hard items: an unavailable request must
return `no_candidates`, not an unsuitable substitute. LeetCode account/submission
access and actual learning effects have not been tested.

Only explicit preferences and session exclusions affect selection. Exclusions
are not mastery, solved status or persistent history. No automatic fallback to
the existing analyzer-dependent ranker is permitted.

Before runtime integration, review the API adapter and dashboard/page cutover,
first-use controls, stable problem identity and preparation handoff, session
lifecycle/account isolation, source maintenance and controlled preview tests.
Durable storage and any future learner-state policy require separate review.
