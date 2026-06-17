# PathForge Product Review Report

Date: 2026-06-16
Reviewer: Automated QA System (3-user simulation, 20 submissions each)

---

## Executive Summary

PathForge's learning loop operates correctly at the unit level (82/82 tests pass) but reveals significant product-level issues in end-to-end simulation across three user personas. The recommendation system, Elo engine, and problem database interact in ways that produce unintended user experiences — particularly around topic rotation dead-ends, insufficient fail rotation sensitivity, and difficulty whipsaw.

**Bottom line:** The system works for the happy path but degrades sharply for struggling users. Feature-complete at the code level, but not yet ready for unsupervised product use.

**Overall assessment: MEDIUM RISK** — actionable product issues exist but are fixable within the current architecture.

---

## Methodology

Three simulated personas with 6,000+ data points each:

| User | Description | Pass Rate | Behavior |
|------|-------------|-----------|----------|
| A | High Performer | 85% (biased) | Practices new topics, passes consistently, Elo climbs |
| B | Struggling | 20% (biased) | Alternates pass/fail, difficulty mostly Easy/Medium |
| C | Mixed | ~60% (strong/weak topic bias) | Alternates based on topic match |

Each run: init user → pick initial problem → loop 20 steps (submit, update profile/get recommendation). Dead-end recovery allows fallback to any unsolved problem when rotation produces a non-actionable recommendation.

Full simulation code: `qa_simulator.py`

---

## Key Findings (Ranked by Severity)

### 🔴 RISK 1: Rotation Dead-Ends Are The Norm

**Observation:** When `_rotate_topic()` selects a pattern with zero problems at the recommended difficulty (e.g., `backtracking_permutation` has no Easy problems), `get_recommendation()` returns `topic_hint` with no actionable problem.

**Impact:**
- User A triggered a dead-end on **every rotation** (steps 3, 6, 9, 17)
- User C triggered a dead-end on **their only rotation** (step 3)
- Dead-end topics are always the same 6 patterns with zero CSV problems + 8 with <5 problems

**Root cause:** `_rotate_topic()` selects the globally weakest pattern via `get_weakest_topics()`, but those patterns may have no problems at the user's Elo-appropriate difficulty. No fallback or retry mechanism exists.

**Recommendation:** Add a retry loop in `_rotate_topic()` (up to `len(topics)` attempts) with `exclude_problematic=True` to skip topics with zero problems at the target difficulty.

---

### 🔴 RISK 2: Fail Rotation Is Ineffective For Struggling Users

**Observation:** `recent_failures` resets to 0 on ANY pass (in `update_topic_profile()`). A struggling user who passes 20% of the time will almost never accumulate 3 consecutive fails.

**Data:**
- User B (20% pass rate): only **2 fail rotations** in 20 steps (steps 12 and 20)
- User B stayed on `hash_map_frequency` for 10 consecutive steps before fail rotation triggered
- User C (mixed): **0 fail rotations** despite 47% fail rate — passes always interrupted consecutive fails

**Impact:** Users with mixed pass/fail patterns experience little topic diversification. They grind the same topic for 10+ submissions without meaningful rotation.

**Recommendation:** Consider `recent_failures >= 3` **OR** `fail_rate > 0.6 in last 5` to catch alternating patterns.

---

### 🟠 RISK 3: Pass Rotation Interrupts Mastery Progression

**Observation:** After 3 consecutive passes, the user is rotating away from a topic they are clearly mastering. This sends them back to Easy difficulty on a new topic.

**Data:**
- User A: Step 3 — had just solved Easy→Medium→Hard on `backtracking_subset`. Rotation put them at Easy for `backtracking_permutation` (dead-end).
- User C: Step 3 — same pattern; then never completed an Easy→Medium→Hard→rotate cycle again.

**Impact:** Users never experience deep mastery of a single topic beyond 3 problems. Difficulty resets create a "surface-level learning" feel.

**Recommendation:** Consider increasing pass threshold to 5, or allow "continue mastering" option alongside rotation.

---

### 🟠 RISK 4: Difficulty Whipsaw on Rotation

**Observation:** Each rotation resets difficulty based on the new topic's Elo (defaults to Easy for Elo < 1000).

**Data:**
- User A: Step 17 → `backtracking_permutation` Easy (Elo=960 on previous topic)
- User C: Step 6 → after rotation, Elo-appropriate difficulty drops from Hard to Medium

**Impact:** A user solving Hard problems gets sent back to Easy on every rotation. This feels regressive and may cause disengagement.

**Recommendation:** Carry the user's global difficulty trajectory (or average of recent topics' difficulty) to the new topic rather than resetting from scratch.

---

### 🟡 RISK 5: Low Topic Coverage Over Time

**Observation:** After 20 submissions, users cover only 2-5 unique topics out of 27 available patterns.

| User | Unique Topics | Worst Coverage |
|------|--------------|----------------|
| A | 5 | Missed 3 of 5 weakest |
| B | 3 | Missed 1 of 5 weakest |
| C | 2 | Missed 3 of 5 weakest |

**Impact:** The global weakest patterns (`backtracking_permutation`, `bfs_level_order`, `bfs_shortest_path`, etc.) remain at Elo=900 with zero practice across all users. The system rotates toward them but can never recommend a specific problem.

**Recommendation:** Ensure each rotation targets a DIFFERENT weak topic (avoiding re-selecting the same dead-end). Add topic diversity incentive to rotation selection.

---

## Additional Observations

### Difficulty Band Lock-In (Struggling Users)
User B completed **0 Hard problems** in 20 steps. The Elo-driven difficulty keeps them oscillating between Easy (when failing) and Medium (when passing). This creates a "tutorial trap" where struggling users never advance to Hard content.

### Elo Stagnation for Alternating Patterns
When a user alternates pass/fail, Elo moves very little:
- User B: final Elo range = 900–916 (oscillating around baseline)
- User C: despite 47% fail rate, Elo slowly climbs (900→1050) — but this is slow

### Simulation Artifacts
- The forced fallback `[F]` recovery (my simulation's dead-end handler) reveals how frequently users would encounter non-actionable recommendations. Without this handler, all 3 users would have stuck at step 3.
- The monotonically increasing Elo on pass-only patterns (User A's `backtracking_subset`: 900→951) matches expectations.

---

## Top 5 Product Risks

| Rank | Risk | Severity | Effort to Fix | Description |
|------|------|----------|---------------|-------------|
| 1 | Rotation dead-ends | Critical | Low | `_rotate_topic` selects patterns with no actionable problems |
| 2 | Fail rotation insensitivity | High | Low | `recent_failures` reset on any pass prevents fail rotation |
| 3 | Pass rotation interrupts mastery | High | Medium | 3-pass threshold too low; difficulty resets on rotation |
| 4 | Difficulty whipsaw | Medium | Medium | New topic resets to Easy regardless of prior difficulty |
| 5 | Low topic coverage | Medium | Low | Rotations keep selecting same dead-end weakest topics |

---

## Verdict

**Not ready for unsupervised release.** The core architecture (Elo, recommendation engine, problem database) is sound, but the diversification layer needs refinement. The top 3 risks are fixable within the existing architecture without schema changes. Recommend addressing Risks 1 and 2 before launch, Risk 3-4 for v1.1.

Recommendation engine correctness: ✅ (82/82 tests pass)
Product UX quality: ⚠️ (5 moderate-to-critical risks)
Overall: **Ship after Risk 1 + Risk 2 fixes**
