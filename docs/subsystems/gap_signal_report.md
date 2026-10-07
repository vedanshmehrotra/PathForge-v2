# Gap Signal Engine — Report

## Algorithm Summary

The Gap Signal Engine is PathForge's first learning layer. It identifies structured
learning signals by analyzing three inputs:

1. **AST Output** — pattern detections and confidence scores from code analysis
2. **Matching Engine Output** — match classification (FULL/PARTIAL/NO) with matched
   and unmatched patterns
3. **User Submission History** — past attempts, failures, and detection confidence

### Signal Computation

For each candidate pattern, `gap_strength` is calculated as:

```
gap_strength = (miss_frequency × 0.5)
             + (recency_weight × 0.3)
             + (confidence_penalty × 0.2)
```

### Candidate Pattern Sources

- **Missing patterns**: patterns present in the LLM's expected solution groups but
  absent from AST detections (from `unmatched_patterns`)
- **Weak signals**: patterns detected with confidence < 0.6, or patterns showing
  inconsistent detection confidence across submissions (std_dev > 0.2)

### Gap Classification

| Level        | Range          |
|--------------|----------------|
| strong_gaps  | ≥ 0.7          |
| moderate_gaps| 0.4 – 0.7      |
| weak_gaps    | < 0.4          |

## Anti-Bias Protection

A pattern is excluded from gap signals if:

- The Matching Engine returns `FULL_MATCH` for the current submission
- All of the user's recent (last 5) submissions for that pattern have
  consistently high confidence (≥ 0.6)

## Temporal Weighting

- Only the **last 5 submissions** are considered for recency weighting
- Older submissions are excluded from recency but counted in frequency
- Recency decays linearly over a 30-day window

## Edge Cases Handled

| Case | Behavior |
|------|----------|
| No submission history | Recency defaults to 0.0; only AST/Matching Engine signals used |
| Empty AST output | All LLM-expected patterns become candidates |
| Full match repeatedly | Anti-bias suppresses all gap signals |
| Partial match | Unmatched patterns are promoted to gap candidates |
| Low-confidence detection | Confidence penalty boosts gap_strength |
| Inconsistent detection | Patterns with fluctuating confidence flagged as weak signals |
| Multiple overlapping patterns | Each pattern scored independently |

## Database Schema

Added `gap_signals` table:

- `user_id` — FK to users
- `pattern_id` — canonical pattern name
- `gap_strength` — computed score [0.0, 1.0]
- `frequency` — number of times pattern appeared in history
- `last_seen` — timestamp of most recent occurrence
- `created_at`, `updated_at` — timestamps
- Unique constraint on `(user_id, pattern_id)`

The `persist_signals()` method upserts records for each computed signal.

## Limitations

- Does not incorporate Elo ratings or topic profile data (future integration)
- Recency decay assumes linear model; exponential might better reflect forgetting
- Inconsistent detection threshold (std_dev > 0.2) is heuristic; may need tuning
- No cross-pattern correlation analysis yet
- Requires submission history to be passed; cannot self-query the database

## Future Improvements

- Integrate with Elo system to weight gap_strength by skill level
- Add pattern co-occurrence analysis (missing pattern A may indicate gap in B)
- Machine-learned gap thresholds instead of hardcoded 0.4/0.7
- Incorporate problem difficulty into gap scoring
- Real-time streaming updates as new submissions arrive
- Confidence calibration against actual user performance data
