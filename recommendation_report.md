# Recommendation Engine — Report

## Algorithm Summary

The Recommendation Engine is PathForge's decision layer. It takes the outputs
of Gap Engine (diagnosis) and Elo System (skill memory) and produces ranked,
diverse problem recommendations.

### Weak Score

For each pattern the user has interacted with:

```
weak_score = (gap_strength × 0.5) + (elo_deficit × 0.5)
```

Where `elo_deficit = max(0, (1200 - elo) / 1200)`.

Patterns the user has solved (passed verdict) get a 50% reduction in weak_score
to avoid recommending already-mastered topics.

### Priority Score

Problems are ranked by:

```
priority_score = weak_score + novelty_bonus + diversity_bonus - recency_penalty
```

| Factor | Value | Condition |
|--------|-------|-----------|
| weak_score | computed | higher = weaker |
| novelty_bonus | +0.20 | pattern NOT in recent submissions |
| diversity_bonus | +0.15 | pattern's category not yet selected |
| recency_penalty | -0.30 | pattern WAS in recent submissions |

### Difficulty Mapping

| Elo Range | Difficulty |
|-----------|------------|
| < 1000    | Easy       |
| 1000–1300 | Medium     |
| > 1300    | Hard       |

### Expected Learning Gain

```
gain = weak_score × 0.7 + (0.2 if unsolved else 0.0)
```

Unsolved problems get a bonus — they represent unknown territory with high
learning potential.

## Recommendation Strategies

| Strategy | Trigger | Behavior |
|----------|---------|----------|
| cold_start_exploration | 0 submissions | Balanced coverage across all available patterns |
| reinforce_weakest | 2+ patterns with weak_score ≥ 0.7 (or 3+ ≥ 0.4) | Prioritize weakest patterns |
| broaden_coverage | All top-5 patterns at or above 1200 Elo | Push into less-practiced categories |
| balanced_maintenance | Default | Mix of weak patterns and diversity |

## Diversity Rules

- Problems are categorized into 6 groups: arrays, trees_graphs, dp, linked_lists,
  binary_search, greedy_backtracking
- The engine attempts problem selection from at least 2 categories
- If the initial selection is mono-category, a diversity pass enriches the batch

## Edge Cases Handled

| Case | Behavior |
|------|----------|
| New user (no Elo) | Cold start — balanced exploration across all patterns with problems |
| No gap signals | Fallback to Elo-only weak score (gap_strength = 0.0) |
| No submission history | All problems treated as unsolved; no recency penalty |
| All patterns equal | Sorted by pattern name; balanced coverage |
| Missing problem bank patterns | Patterns without problems are excluded from candidates |
| Solved patterns | 50% weak_score reduction prevents re-recommendation |
| Repeated failures | Pattern stays in weak set; recency penalty doesn't exclude |
| Multi-pattern problems | All target patterns reported; problem selected once |

## Inputs

1. **Problem Bank** — list of problem dicts with id, title, difficulty, pattern (JSON array), acceptance_rate
2. **user_pattern_elo** — dict of {pattern_id: elo}
3. **gap_signals** — list of {pattern_id, gap_strength}
4. **recent_submissions** — list of {detected_pattern, verdict, problem_id}

## Output

```
{
  "user_id": str,
  "recommended_problems": [
    {
      "problem_id": str,
      "target_patterns": [str],
      "reason": str,
      "difficulty_score": float,
      "expected_learning_gain": float
    }
  ],
  "summary": {
    "primary_weak_patterns": [str],
    "focus_area": str,
    "recommendation_strategy": str
  }
}
```

## Limitations

- Problem bank must be provided at construction time; no live DB queries
- No multi-user collaborative filtering
- No reinforcement learning — purely deterministic scoring
- Category map is hardcoded; new patterns require manual mapping
- Expected learning gain is heuristic, not empirically calibrated

## Future Improvements

- Dynamic difficulty adjustment based on recent success rate
- Spaced repetition scheduling for review of older patterns
- Collaborative filtering across user cohorts
- A/B test framework for strategy effectiveness
- Prerequisite chain awareness (learn X before Y)
