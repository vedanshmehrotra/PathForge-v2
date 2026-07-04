# Elo System — Report

## Algorithm Summary

The Elo System is PathForge's long-term skill memory layer. It maintains a
continuous per-pattern rating for each user, updated after every submission.

### Core Formula

For each pattern:

```
expected = 1 / (1 + 10^((opponent - elo) / 400))
elo_new = elo_old + K × (score - expected)
```

### Score Mapping

| Matching Engine Result | Base Score |
|------------------------|------------|
| FULL_MATCH             | 1.0        |
| PARTIAL_MATCH          | 0.5        |
| NO_MATCH               | 0.0        |

### K-Factor Rules

| Condition | Effect |
|-----------|--------|
| Default   | K = 32  |
| gap_strength > 0.5   | K += 16 (faster learning) |
| 3+ submissions in history | K -= 8 (stable learners) |
| Bounds    | K ∈ [8, 64] |

### Gap Signal Penalty

When `gap_strength > 0.6`, the raw score is reduced by 0.3 before the Elo
update. When `gap_strength > 0.3`, it is reduced by 0.15. This prevents a
user from gaining Elo on patterns they are fundamentally weak at.

### AST Reinforcement

If AST detects a pattern with confidence ≥ 0.8, the opponent rating is
increased (+200) making it harder to gain Elo — a higher bar for patterns
the code itself demonstrates.

If Matching Engine returns NO_MATCH but AST detects the pattern,
a minimum score of 0.2 is applied to prevent total score collapse from
conflicting signals.

### Anti-Drift Protection

Repeated FULL_MATCH → diminishing returns:
- 3+ consecutive FULL_MATCH → score decays by 0.1 per extra match
- Floor at 0.5× score multiplier

Repeated NO_MATCH → saturation penalty:
- 3+ consecutive NO_MATCH → score decays by 0.15 per extra match
- Floor at 0.3× score multiplier

## Cold Start

Patterns with no prior Elo initialize at 1200.0. Minimum Elo is 400.0.

## Database Schema

`user_pattern_elo` table:
- `user_id` — FK to users
- `pattern_id` — canonical pattern name
- `elo` — current rating [400.0, ∞)
- `last_updated` — timestamp of last Elo update
- `created_at`, `updated_at`
- Unique constraint on `(user_id, pattern_id)`

## Inputs

1. **Gap Signals** — used to penalize scores on known-weak patterns
2. **Matching Engine Result** — primary correctness signal
3. **AST Output** — optional reinforcement signal for conflicting cases
4. **Current Elos** — map of existing per-pattern ratings
5. **Pattern Histories** — recent match results for anti-drift

## Output

```
{
  "user_id": str,
  "pattern_elo_updates": [{ pattern_id, old_elo, new_elo, delta, confidence_weight }],
  "global_summary": { average_elo_change, strongest_improvement_patterns, weakest_patterns }
}
```

## Edge Cases Handled

| Case | Behavior |
|------|----------|
| No gap signals | Only Matching Engine signal used |
| No AST output | No reinforcement; opponent defaults to 1200 |
| Conflicting AST vs ME | AST provides minimum score floor |
| First-time user | Cold start at 1200 per pattern |
| Repeated success | Diminishing returns prevents inflation |
| Repeated failure | Saturation prevents runaway decline |
| Elo floor | Never drops below 400 |

## Limitations

- Opponent rating uses fixed 1200 baseline (no per-problem difficulty)
- No cross-pattern Elo correlation
- Confidence weight is informational only (not used in Elo formula)
- Gap penalty is heuristic; no calibration against real outcome data
- History tracking requires caller to pass pattern histories

## Future Improvements

- Integrate per-problem difficulty into opponent rating
- Dynamic K-factor based on Elo volatility (not just count)
- Cross-pattern transfer learning (related patterns share Elo)
- Decay inactive pattern Elo over time
- Confidence-weighted updates (use confidence_weight in formula)
