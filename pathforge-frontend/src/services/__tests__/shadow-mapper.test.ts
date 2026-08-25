/**
 * Tests for the Shadow Analysis Presentation Mapper.
 *
 * These tests verify that internal shadow analysis data is correctly
 * mapped to user-friendly display text. No React rendering required.
 *
 * Regression tests ensure:
 * - CONFIRMED never shows "Approach unclear"
 * - UNRESOLVED shows "Approach unclear" when no candidates
 * - Developer details are collapsed by default (see experimental-panel.test.tsx)
 * - Missing shadow data hides the experimental card
 * - Confidence is always '—' for UNRESOLVED
 */

import { describe, it, expect } from 'vitest'
import { mapShadowToDisplay } from '../../services/shadow-mapper'
import type { ShadowAnalysisResult } from '../../types/api'

// ============================================================
// Test fixtures
// ============================================================

function makeShadowResult(overrides: Partial<ShadowAnalysisResult> = {}): ShadowAnalysisResult {
  return {
    structural_facts: [],
    technique_evidence: [],
    strategy_evidence: [],
    match_outcome: null,
    extractor_version: '1.0.0',
    elapsed_ms: 10.0,
    ...overrides,
  }
}

function makeMatchOutcome(overrides: Record<string, unknown> = {}) {
  return {
    outcome: 'UNRESOLVED' as const,
    satisfied_group_ids: [] as string[],
    authority_tier: 'llm_proposed',
    primary_strategy: null,
    reasoning: [] as string[],
    technique_count: 0,
    strategy_count: 0,
    fact_count: 0,
    ...overrides,
  }
}

// ============================================================
// Tests: visibility
// ============================================================

describe('mapShadowToDisplay — visibility', () => {
  it('returns visible: false when shadow is null', () => {
    const result = mapShadowToDisplay(null)
    expect(result.visible).toBe(false)
  })

  it('returns visible: false when shadow is undefined', () => {
    const result = mapShadowToDisplay(undefined)
    expect(result.visible).toBe(false)
  })

  it('returns visible: false when match_outcome is null', () => {
    const shadow = makeShadowResult({ match_outcome: null })
    const result = mapShadowToDisplay(shadow)
    expect(result.visible).toBe(false)
  })

  it('returns visible: true when match_outcome is present', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONFIRMED' }),
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.visible).toBe(true)
  })
})

// ============================================================
// Tests: CONFIRMED state
// ============================================================

describe('mapShadowToDisplay — CONFIRMED', () => {
  it('shows likely_match status', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONFIRMED' }),
      strategy_evidence: [
        {
          strategy_id: 'two_pointers_opposite',
          strategy_version: '1.0.0',
          supporting_technique_ids: ['bidirectional_index_scan'],
          supporting_fact_ids: [],
          confidence: 0.9,
          problem_context_signals: {},
        },
      ],
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.visible).toBe(true)
    expect(result.status).toBe('likely_match')
    expect(result.statusLabel).toBe('Likely match')
  })

  it('shows human-readable strategy name', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONFIRMED' }),
      strategy_evidence: [
        {
          strategy_id: 'binary_search',
          strategy_version: '1.0.0',
          supporting_technique_ids: [],
          supporting_fact_ids: [],
          confidence: 0.85,
          problem_context_signals: {},
        },
      ],
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.approaches).toEqual(['Binary Search'])
  })

  it('shows High confidence for score >= 0.8', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONFIRMED' }),
      strategy_evidence: [
        {
          strategy_id: 'sliding_window',
          strategy_version: '1.0.0',
          supporting_technique_ids: [],
          supporting_fact_ids: [],
          confidence: 0.85,
          problem_context_signals: {},
        },
      ],
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.confidence).toBe('High')
  })

  it('shows Medium confidence for score 0.5-0.8', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONFIRMED' }),
      strategy_evidence: [
        {
          strategy_id: 'dp_top_down',
          strategy_version: '1.0.0',
          supporting_technique_ids: [],
          supporting_fact_ids: [],
          confidence: 0.6,
          problem_context_signals: {},
        },
      ],
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.confidence).toBe('Medium')
  })

  it('generates plain-language explanation for CONFIRMED with strategy', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONFIRMED' }),
      strategy_evidence: [
        {
          strategy_id: 'two_pointers_opposite',
          strategy_version: '1.0.0',
          supporting_technique_ids: [],
          supporting_fact_ids: [],
          confidence: 0.9,
          problem_context_signals: {},
        },
      ],
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.explanation).toContain('Two Pointers')
    // Must not contain internal technique jargon
    expect(result.explanation).not.toContain('bidirectional_index_scan')
    expect(result.explanation).not.toContain('exhibits')
  })

  it('does NOT show "Approach unclear" when CONFIRMED with no strategies but has techniques', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONFIRMED' }),
      strategy_evidence: [],
      technique_evidence: [
        {
          technique_id: 'sequential_accumulation',
          technique_version: '1.0.0',
          supporting_fact_ids: [],
          presence_confidence: 0.85,
          centrality: 0.6,
        },
      ],
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.status).toBe('likely_match')
    // Should fall back to technique name, NOT show "Approach unclear"
    expect(result.approaches).not.toContain('Approach unclear')
    expect(result.approaches[0]).toBe('Running total')
  })

  it('does NOT show "Approach unclear" when CONFIRMED with no strategies and no techniques', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONFIRMED' }),
      strategy_evidence: [],
      technique_evidence: [],
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.status).toBe('likely_match')
    // CONFIRMED with nothing should still NOT be "Approach unclear"
    // It shows "Approaches detected" since there are no specific approaches
    expect(result.approaches).not.toContain('Approach unclear')
  })
})

// ============================================================
// Tests: UNRESOLVED state
// ============================================================

describe('mapShadowToDisplay — UNRESOLVED', () => {
  it('shows not_enough_evidence status', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'UNRESOLVED' }),
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.status).toBe('not_enough_evidence')
    expect(result.statusLabel).toBe('Not enough evidence')
  })

  it('shows confidence as dash for UNRESOLVED', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'UNRESOLVED' }),
      strategy_evidence: [
        {
          strategy_id: 'binary_search',
          strategy_version: '1.0.0',
          supporting_technique_ids: [],
          supporting_fact_ids: [],
          confidence: 0.9,
          problem_context_signals: {},
        },
      ],
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.confidence).toBe('—')
  })

  it('shows generic explanation when no techniques detected', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'UNRESOLVED' }),
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.explanation).toContain("isn't enough information")
    // Must not contain technical terms
    expect(result.explanation).not.toContain('signals')
  })

  it('shows "Approach unclear" when UNRESOLVED with no strategies', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'UNRESOLVED' }),
      strategy_evidence: [],
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.approaches).toEqual(['Approach unclear'])
  })

  it('shows up to 2 candidate approaches for UNRESOLVED', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'UNRESOLVED' }),
      strategy_evidence: [
        {
          strategy_id: 'binary_search',
          strategy_version: '1.0.0',
          supporting_technique_ids: [],
          supporting_fact_ids: [],
          confidence: 0.6,
          problem_context_signals: {},
        },
        {
          strategy_id: 'two_pointers_opposite',
          strategy_version: '1.0.0',
          supporting_technique_ids: [],
          supporting_fact_ids: [],
          confidence: 0.4,
          problem_context_signals: {},
        },
      ],
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.approaches).toHaveLength(2)
    expect(result.approaches).toContain('Binary Search')
    expect(result.approaches).toContain('Two Pointers')
  })

  it('shows "Approach unclear" for >2 candidates', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'UNRESOLVED' }),
      strategy_evidence: [
        {
          strategy_id: 'binary_search',
          strategy_version: '1.0.0',
          supporting_technique_ids: [],
          supporting_fact_ids: [],
          confidence: 0.4,
          problem_context_signals: {},
        },
        {
          strategy_id: 'two_pointers_opposite',
          strategy_version: '1.0.0',
          supporting_technique_ids: [],
          supporting_fact_ids: [],
          confidence: 0.35,
          problem_context_signals: {},
        },
        {
          strategy_id: 'sliding_window',
          strategy_version: '1.0.0',
          supporting_technique_ids: [],
          supporting_fact_ids: [],
          confidence: 0.3,
          problem_context_signals: {},
        },
      ],
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.approaches).toEqual(['Approach unclear'])
  })
})

// ============================================================
// Tests: CONTRADICTED state
// ============================================================

describe('mapShadowToDisplay — CONTRADICTED', () => {
  it('shows possible_mismatch status', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONTRADICTED' }),
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.status).toBe('possible_mismatch')
    expect(result.statusLabel).toBe('Possible mismatch')
  })

  it('shows "Approach unclear" for CONTRADICTED', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONTRADICTED' }),
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.approaches).toEqual(['Approach unclear'])
  })

  it('shows explanation about different approach', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONTRADICTED' }),
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.explanation).toContain('different approach')
  })

  it('shows dash confidence for CONTRADICTED', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONTRADICTED' }),
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.confidence).toBe('—')
  })
})

// ============================================================
// Tests: Status / approach consistency (regression)
// ============================================================

describe('mapShadowToDisplay — status/approach consistency', () => {
  it('CONFIRMED always shows a concrete approach, never "Approach unclear"', () => {
    // Test all combinations: with strategies, without strategies but with techniques, empty
    const withStrategy = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONFIRMED' }),
      strategy_evidence: [{ strategy_id: 'binary_search', strategy_version: '1.0', supporting_technique_ids: [], supporting_fact_ids: [], confidence: 0.9, problem_context_signals: {} }],
    })
    const noStrategyWithTech = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONFIRMED' }),
      strategy_evidence: [],
      technique_evidence: [{ technique_id: 'sequential_accumulation', technique_version: '1.0', supporting_fact_ids: [], presence_confidence: 0.8, centrality: 0.6 }],
    })
    const empty = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONFIRMED' }),
      strategy_evidence: [],
      technique_evidence: [],
    })

    expect(mapShadowToDisplay(withStrategy).approaches).not.toContain('Approach unclear')
    expect(mapShadowToDisplay(noStrategyWithTech).approaches).not.toContain('Approach unclear')
    expect(mapShadowToDisplay(empty).approaches).not.toContain('Approach unclear')
  })

  it('UNRESOLVED always shows "Approach unclear" when no strategy candidates', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'UNRESOLVED' }),
      strategy_evidence: [],
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.approaches).toEqual(['Approach unclear'])
  })

  it('status label matches status key', () => {
    const confirmed = makeShadowResult({ match_outcome: makeMatchOutcome({ outcome: 'CONFIRMED' }) })
    const unresolved = makeShadowResult({ match_outcome: makeMatchOutcome({ outcome: 'UNRESOLVED' }) })
    const contradicted = makeShadowResult({ match_outcome: makeMatchOutcome({ outcome: 'CONTRADICTED' }) })

    expect(mapShadowToDisplay(confirmed).statusLabel).toBe('Likely match')
    expect(mapShadowToDisplay(unresolved).statusLabel).toBe('Not enough evidence')
    expect(mapShadowToDisplay(contradicted).statusLabel).toBe('Possible mismatch')
  })
})

// ============================================================
// Tests: malformed / missing data
// ============================================================

describe('mapShadowToDisplay — malformed data', () => {
  it('handles empty strategy_evidence for CONFIRMED', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONFIRMED' }),
      strategy_evidence: [],
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.visible).toBe(true)
    expect(result.approaches).toBeDefined()
    expect(result.approaches).not.toContain('Approach unclear')
  })

  it('handles empty technique_evidence for UNRESOLVED', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'UNRESOLVED' }),
      technique_evidence: [],
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.visible).toBe(true)
  })

  it('handles unknown strategy_id gracefully', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONFIRMED' }),
      strategy_evidence: [
        {
          strategy_id: 'unknown_strategy_xyz',
          strategy_version: '1.0.0',
          supporting_technique_ids: [],
          supporting_fact_ids: [],
          confidence: 0.9,
          problem_context_signals: {},
        },
      ],
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.visible).toBe(true)
    // Falls back to the raw ID
    expect(result.approaches).toContain('unknown_strategy_xyz')
  })

  it('handles unknown technique_id gracefully', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'UNRESOLVED' }),
      technique_evidence: [
        {
          technique_id: 'unknown_tech',
          technique_version: '1.0.0',
          supporting_fact_ids: [],
          presence_confidence: 0.7,
          centrality: 0.5,
        },
      ],
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.visible).toBe(true)
    // Explanation should be generic, not expose raw IDs
    expect(result.explanation).toContain("isn't enough information")
  })
})

// ============================================================
// Tests: production result unchanged
// ============================================================

describe('mapShadowToDisplay — production unchanged', () => {
  it('does not modify the input shadow object', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONFIRMED' }),
      strategy_evidence: [
        {
          strategy_id: 'binary_search',
          strategy_version: '1.0.0',
          supporting_technique_ids: [],
          supporting_fact_ids: [],
          confidence: 0.85,
          problem_context_signals: {},
        },
      ],
    })
    const original = JSON.stringify(shadow)
    mapShadowToDisplay(shadow)
    expect(JSON.stringify(shadow)).toBe(original)
  })

  it('developerDetails contains raw internal data', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({
        outcome: 'CONFIRMED',
        authority_tier: 'structurally_observed',
        fact_count: 12,
      }),
      strategy_evidence: [
        {
          strategy_id: 'two_pointers_opposite',
          strategy_version: '1.0.0',
          supporting_technique_ids: [],
          supporting_fact_ids: [],
          confidence: 0.9,
          problem_context_signals: {},
        },
      ],
      elapsed_ms: 15.3,
      extractor_version: '1.0.0',
    })
    const result = mapShadowToDisplay(shadow)
    expect(result.developerDetails.outcome).toBe('CONFIRMED')
    expect(result.developerDetails.authorityTier).toBe('structurally_observed')
    expect(result.developerDetails.elapsedMs).toBe(15.3)
    expect(result.developerDetails.factCount).toBe(12)
  })
})

// ============================================================
// Tests: plain language (no technical jargon in user-facing text)
// ============================================================

describe('mapShadowToDisplay — plain language', () => {
  it('CONFIRMED explanation does not contain internal IDs', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'CONFIRMED' }),
      strategy_evidence: [
        {
          strategy_id: 'two_pointers_opposite',
          strategy_version: '1.0.0',
          supporting_technique_ids: [],
          supporting_fact_ids: [],
          confidence: 0.9,
          problem_context_signals: {},
        },
      ],
      technique_evidence: [
        {
          technique_id: 'bidirectional_index_scan',
          technique_version: '1.0.0',
          supporting_fact_ids: [],
          presence_confidence: 0.9,
          centrality: 0.85,
        },
      ],
    })
    const result = mapShadowToDisplay(shadow)
    // Should contain human-readable names
    expect(result.explanation).toContain('Two Pointers')
    // Should NOT contain raw IDs or technical jargon
    expect(result.explanation).not.toContain('two_pointers_opposite')
    expect(result.explanation).not.toContain('bidirectional_index_scan')
    expect(result.explanation).not.toContain('exhibits')
    expect(result.explanation).not.toContain('patterns, consistent')
  })

  it('UNRESOLVED explanation is plain language', () => {
    const shadow = makeShadowResult({
      match_outcome: makeMatchOutcome({ outcome: 'UNRESOLVED' }),
      technique_evidence: [
        {
          technique_id: 'sequential_accumulation',
          technique_version: '1.0.0',
          supporting_fact_ids: [],
          presence_confidence: 0.85,
          centrality: 0.6,
        },
      ],
    })
    const result = mapShadowToDisplay(shadow)
    // Should NOT contain raw technique IDs
    expect(result.explanation).not.toContain('sequential_accumulation')
    expect(result.explanation).not.toContain('signals')
  })
})
