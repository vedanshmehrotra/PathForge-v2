/**
 * Shadow Analysis Presentation Mapper
 *
 * Converts internal shadow analysis data (strategy IDs, technique IDs,
 * satisfaction scores, outcomes) into simple, user-friendly text.
 *
 * This module is the ONLY place where internal IDs are mapped to
 * human-readable names. The UI should never reference raw IDs directly.
 */

import type { ShadowAnalysisResult } from '@/types/api'

// ============================================================
// Human-readable approach names (strategy_id → display name)
// ============================================================

const STRATEGY_NAMES: Record<string, string> = {
  two_pointers_opposite: 'Two Pointers',
  binary_search: 'Binary Search',
  sliding_window: 'Sliding Window',
  dfs_backtracking: 'DFS / Backtracking',
  bfs_shortest_path: 'BFS / Shortest Path',
  dp_top_down: 'Dynamic Programming (Top-Down)',
  dp_bottom_up: 'Dynamic Programming (Bottom-Up)',
  union_find: 'Union-Find',
  monotonic_stack_strategy: 'Monotonic Stack',
}

const TECHNIQUE_NAMES: Record<string, string> = {
  sequential_accumulation: 'Sequential Accumulation',
  bidirectional_index_scan: 'Bidirectional Index Scan',
  recursive_branching: 'Recursive Branching',
  carry_propagation: 'Carry Propagation',
  loop_state_tracking: 'Loop State Tracking',
  iterative_table_filling: 'Iterative Table Filling',
  linked_list_traversal: 'Linked List Traversal',
  fixed_window_maintenance: 'Fixed Window Maintenance',
  monotonic_stack_maintenance: 'Monotonic Stack',
}

// ============================================================
// Confidence level mapping
// ============================================================

function confidenceLevel(score: number): 'High' | 'Medium' | 'Low' {
  if (score >= 0.8) return 'High'
  if (score >= 0.5) return 'Medium'
  return 'Low'
}

// ============================================================
// Outcome status mapping
// ============================================================

type OutcomeStatus = 'likely_match' | 'not_enough_evidence' | 'possible_mismatch'

function outcomeStatus(
  outcome: string,
  _satisfactionScore: number,
): OutcomeStatus {
  switch (outcome) {
    case 'CONFIRMED':
      return 'likely_match'
    case 'CONTRADICTED':
      return 'possible_mismatch'
    case 'UNRESOLVED':
    default:
      return 'not_enough_evidence'
  }
}

// ============================================================
// Short explanation generation
// ============================================================

function generateExplanation(
  outcome: string,
  strategies: string[],
  techniques: string[],
  reasoning: string[],
): string {
  if (outcome === 'CONFIRMED' && strategies.length > 0) {
    const name = STRATEGY_NAMES[strategies[0]] ?? strategies[0]
    const techNames = techniques
      .map((t) => TECHNIQUE_NAMES[t] ?? t)
      .slice(0, 2)
    if (techNames.length > 0) {
      return `The code exhibits ${techNames.join(' and ')} patterns, consistent with a ${name} approach.`
    }
    return `The code patterns are consistent with a ${name} approach.`
  }

  if (outcome === 'CONTRADICTED') {
    return 'The code appears to use a different approach from the one expected for this problem.'
  }

  // UNRESOLVED
  if (techniques.length === 0) {
    return 'The code contains useful signals, but there isn\'t enough evidence to identify the approach confidently.'
  }
  const techNames = techniques
    .map((t) => TECHNIQUE_NAMES[t] ?? t)
    .slice(0, 2)
  return `The code shows ${techNames.join(' and ')} signals, but there isn\'t enough evidence to confirm a specific approach.`
}

// ============================================================
// Public API: Map shadow analysis to display data
// ============================================================

export interface ShadowDisplayData {
  /** Whether to show the experimental panel at all */
  visible: boolean

  /** Primary status: 'likely_match' | 'not_enough_evidence' | 'possible_mismatch' */
  status: OutcomeStatus

  /** Human-readable status label */
  statusLabel: string

  /** Human-readable approach name(s) */
  approaches: string[]

  /** Confidence as user-friendly text */
  confidence: 'High' | 'Medium' | 'Low' | '—'

  /** One short explanation */
  explanation: string

  /** Internal data for developer details (hidden by default) */
  developerDetails: {
    outcome: string
    strategies: Array<{ id: string; name: string; confidence: number }>
    techniques: Array<{ id: string; name: string; confidence: number }>
    satisfactionScore: number | null
    authorityTier: string
    elapsedMs: number
    extractorVersion: string
    factCount: number
    reasoning: string[]
  }
}

const STATUS_LABELS: Record<OutcomeStatus, string> = {
  likely_match: 'Likely match',
  not_enough_evidence: 'Not enough evidence',
  possible_mismatch: 'Possible mismatch',
}

/**
 * Map a ShadowAnalysisResult from the API into user-friendly display data.
 * Returns { visible: false } if the shadow analysis is absent or invalid.
 */
export function mapShadowToDisplay(
  shadow: ShadowAnalysisResult | null | undefined,
): ShadowDisplayData {
  // Hidden by default — no shadow data means no panel
  if (!shadow || !shadow.match_outcome) {
    return {
      visible: false,
      status: 'not_enough_evidence',
      statusLabel: '',
      approaches: [],
      confidence: '—',
      explanation: '',
      developerDetails: {
        outcome: '',
        strategies: [],
        techniques: [],
        satisfactionScore: null,
        authorityTier: '',
        elapsedMs: 0,
        extractorVersion: '',
        factCount: 0,
        reasoning: [],
      },
    }
  }

  const outcome = shadow.match_outcome
  const strategies = shadow.strategy_evidence ?? []
  const techniques = shadow.technique_evidence ?? []

  // Sort strategies by confidence descending
  const sortedStrategies = [...strategies].sort(
    (a, b) => b.confidence - a.confidence,
  )

  // Map strategy IDs to human-readable names
  const strategyNames = sortedStrategies
    .map((s) => STRATEGY_NAMES[s.strategy_id] ?? s.strategy_id)
    .filter(Boolean)

  // For CONFIRMED: show the primary strategy
  // For UNRESOLVED/CONTRADICTED: show up to 2 candidate names
  let approaches: string[]
  if (outcome.outcome === 'CONFIRMED') {
    approaches = strategyNames.length > 0 ? [strategyNames[0]] : []
  } else if (outcome.outcome === 'UNRESOLVED' && strategyNames.length <= 2) {
    approaches = strategyNames
  } else if (outcome.outcome === 'UNRESOLVED' && strategyNames.length > 2) {
    // Too many candidates → show "unclear"
    approaches = []
  } else {
    approaches = []
  }

  // Confidence from the best strategy or best technique
  const bestConfidence =
    sortedStrategies.length > 0
      ? sortedStrategies[0].confidence
      : techniques.length > 0
        ? Math.max(...techniques.map((t) => t.presence_confidence))
        : 0

  const status = outcomeStatus(outcome.outcome, bestConfidence)
  const techniqueIds = techniques.map((t) => t.technique_id)

  const explanation = generateExplanation(
    outcome.outcome,
    strategyIds(strategies),
    techniqueIds,
    outcome.reasoning ?? [],
  )

  return {
    visible: true,
    status,
    statusLabel: STATUS_LABELS[status],
    approaches:
      approaches.length > 0 ? approaches : ['Approach unclear'],
    confidence: outcome.outcome === 'UNRESOLVED' ? '—' : confidenceLevel(bestConfidence),
    explanation,
    developerDetails: {
      outcome: outcome.outcome,
      strategies: sortedStrategies.map((s) => ({
        id: s.strategy_id,
        name: STRATEGY_NAMES[s.strategy_id] ?? s.strategy_id,
        confidence: s.confidence,
      })),
      techniques: techniques.map((t) => ({
        id: t.technique_id,
        name: TECHNIQUE_NAMES[t.technique_id] ?? t.technique_id,
        confidence: t.presence_confidence,
      })),
      satisfactionScore: bestConfidence,
      authorityTier: outcome.authority_tier ?? '',
      elapsedMs: shadow.elapsed_ms ?? 0,
      extractorVersion: shadow.extractor_version ?? '',
      factCount: outcome.fact_count ?? 0,
      reasoning: outcome.reasoning ?? [],
    },
  }
}

function strategyIds(strategies: { strategy_id: string }[]): string[] {
  return strategies.map((s) => s.strategy_id)
}
