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
  sequential_accumulation: 'Running total',
  bidirectional_index_scan: 'Two-way scan',
  recursive_branching: 'Recursive branching',
  carry_propagation: 'Carry propagation',
  loop_state_tracking: 'State tracking in loops',
  iterative_table_filling: 'Table building',
  linked_list_traversal: 'Linked list walk',
  fixed_window_maintenance: 'Fixed window',
  monotonic_stack_maintenance: 'Monotonic stack',
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
  _reasoning: string[],
): string {
  if (outcome === 'CONFIRMED' && strategies.length > 0) {
    const name = STRATEGY_NAMES[strategies[0]] ?? strategies[0]
    return `The solution follows a ${name} approach for this problem.`
  }

  if (outcome === 'CONFIRMED' && techniques.length > 0) {
    const techName = TECHNIQUE_NAMES[techniques[0]] ?? techniques[0]
    return `The solution uses ${techName.toLowerCase()}, which matches the expected approach.`
  }

  if (outcome === 'CONFIRMED') {
    return 'The solution matches the expected approach for this problem.'
  }

  if (outcome === 'CONTRADICTED') {
    return 'The code appears to use a different approach from what is expected for this problem.'
  }

  // UNRESOLVED
  return 'The code contains some relevant patterns, but there isn\'t enough information to confirm the approach with confidence.'
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

  // Map technique IDs to user-friendly names for fallback display
  const techniqueNames = techniques
    .map((t) => TECHNIQUE_NAMES[t.technique_id] ?? t.technique_id)
    .filter(Boolean)

  // Build the approach list depending on outcome.
  // CONFIRMED: show the primary strategy (or technique fallback)
  // UNRESOLVED: show up to 2 candidate names (or 'unclear' if too many)
  // CONTRADICTED: always 'unclear'
  let approaches: string[]
  if (outcome.outcome === 'CONFIRMED') {
    approaches = strategyNames.length > 0 ? [strategyNames[0]] : techniqueNames.length > 0 ? [techniqueNames[0]] : []
  } else if (outcome.outcome === 'UNRESOLVED' && strategyNames.length <= 2 && strategyNames.length > 0) {
    approaches = strategyNames
  } else if (outcome.outcome === 'UNRESOLVED' && strategyNames.length > 2) {
    approaches = [] // too many candidates
  } else {
    approaches = []
  }

  // Confidence from the best strategy or best technique (only meaningful for CONFIRMED)
  const bestConfidence =
    outcome.outcome === 'CONFIRMED'
      ? sortedStrategies.length > 0
        ? sortedStrategies[0].confidence
        : techniques.length > 0
          ? Math.max(...techniques.map((t) => t.presence_confidence))
          : 0
      : 0

  const status = outcomeStatus(outcome.outcome, bestConfidence)
  const explanation = generateExplanation(
    outcome.outcome,
    strategyIds(strategies),
    techniqueNames,
    outcome.reasoning ?? [],
  )

  return {
    visible: true,
    status,
    statusLabel: STATUS_LABELS[status],
    approaches:
      approaches.length > 0 ? approaches
        : outcome.outcome === 'CONFIRMED' ? ['Approach detected']
        : ['Approach unclear'],
    confidence: outcome.outcome === 'CONFIRMED' ? confidenceLevel(bestConfidence) : '—',
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
