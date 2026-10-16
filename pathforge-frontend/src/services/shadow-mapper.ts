/**
 * Present canonical B3 coverage and B4 selection without changing their decisions.
 * Older matching and raw evidence remain available for diagnostics.
 */
import type { ShadowAnalysisResult } from '@/types/api'

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
  hash_lookup: 'Hash lookup',
  candidate_selection: 'Candidate selection',
  sequential_accumulation: 'Running total',
  bidirectional_index_scan: 'Two-way scan',
  forward_pointer_advance: 'Forward pointer advance',
  recursive_branching: 'Recursive branching',
  carry_propagation: 'Carry propagation',
  loop_state_tracking: 'State tracking in loops',
  iterative_table_filling: 'Table building',
  linked_list_traversal: 'Linked list walk',
  fixed_window_maintenance: 'Fixed window',
  monotonic_stack_maintenance: 'Monotonic stack',
}

function displayName(id: string, names: Record<string, string>): string {
  return names[id] ?? id.replace(/_/g, ' ').replace(/^./, initial => initial.toUpperCase())
}

// Retain the existing display bands; confidence comes only from B4's selected candidate.
function confidenceLevel(score: number): 'High' | 'Medium' | 'Low' {
  if (score >= 0.8) return 'High'
  if (score >= 0.5) return 'Medium'
  return 'Low'
}

function confirmedSelection(shadow: ShadowAnalysisResult): { id: string; confidence: number } | null {
  const coverage = shadow.coverage
  const selection = shadow.strategy_selection
  const primary = selection?.submission
  if (!coverage || coverage.no_ground_truth !== false || !Array.isArray(coverage.families)
      || !selection || !Array.isArray(selection.families) || !primary
      || primary.scope !== 'submission' || typeof primary.selected !== 'string' || !primary.selected
      || primary.ambiguity !== false || primary.tie_resolved !== false
      || !Array.isArray(primary.candidates)) return null

  const selected = primary.selected
  const candidates = primary.candidates.filter(c => c?.concept_id === selected)
  if (candidates.length !== 1) return null
  const confidence = candidates[0].confidence
  if (typeof confidence !== 'number' || !Number.isFinite(confidence) || confidence < 0 || confidence > 1) return null

  // B3's aggregate is a measurement, not a global verdict. Join an actually
  // confirmed family to its B4 primary; never choose/rank a replacement in the UI.
  const familyIds = coverage.families.map(f => f?.family_id)
  if (familyIds.some(id => typeof id !== 'string' || !id) || new Set(familyIds).size !== familyIds.length) return null
  const established = coverage.families.some(family => {
    if (family.coverage_state !== 'CONFIRMED' || !Array.isArray(family.conclusion_eligible_present)
        || !family.conclusion_eligible_present.includes(selected)) return false
    const familySelections = selection.families.filter(f => f?.family_id === family.family_id)
    if (familySelections.length !== 1) return false
    const scoped = familySelections[0]
    if (scoped.scope !== 'family' || scoped.selected !== selected || scoped.ambiguity !== false
        || scoped.tie_resolved !== false || !Array.isArray(scoped.candidates)) return false
    const scopedCandidates = scoped.candidates.filter(c => c?.concept_id === selected)
    return scopedCandidates.length === 1 && scopedCandidates[0].confidence === confidence
  })
  return established ? { id: selected, confidence } : null
}

type OutcomeStatus = 'likely_match' | 'not_enough_evidence' | 'possible_mismatch'

export interface ShadowDisplayData {
  visible: boolean
  status: OutcomeStatus
  statusLabel: string
  approaches: string[]
  techniques: string[]
  confidence: 'High' | 'Medium' | 'Low' | '—'
  explanation: string
  developerDetails: {
    outcome: string
    canonicalPrimary: string | null
    families: Array<{ id: string; state: string }>
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

export function mapShadowToDisplay(shadow: ShadowAnalysisResult | null | undefined): ShadowDisplayData {
  const visible = !!shadow && !!(shadow.match_outcome || shadow.coverage || shadow.strategy_selection)
  const outcome = shadow?.match_outcome
  const strategies = (Array.isArray(shadow?.strategy_evidence) ? shadow.strategy_evidence : [])
    .filter(s => s && typeof s.strategy_id === 'string')
  const techniques = (Array.isArray(shadow?.technique_evidence) ? shadow.technique_evidence : [])
    .filter(t => t && typeof t.technique_id === 'string')
  const confirmed = shadow ? confirmedSelection(shadow) : null
  const techniqueNames = [...new Set(techniques.map(t => displayName(t.technique_id, TECHNIQUE_NAMES)))]
  const selectedName = confirmed ? displayName(confirmed.id, STRATEGY_NAMES) : null

  return {
    visible,
    status: confirmed ? 'likely_match' : 'not_enough_evidence',
    statusLabel: visible ? confirmed ? 'Observed strategy' : 'Not enough evidence' : '',
    approaches: visible ? selectedName ? [selectedName] : ['Approach unclear'] : [],
    techniques: techniqueNames,
    confidence: confirmed ? confidenceLevel(confirmed.confidence) : '—',
    explanation: !visible ? '' : confirmed
      ? `The code contains confirmed ${selectedName} strategy evidence.`
      : 'The available evidence does not establish a confirmed primary strategy.',
    developerDetails: {
      outcome: outcome?.outcome ?? '',
      canonicalPrimary: typeof shadow?.strategy_selection?.submission?.selected === 'string'
        ? shadow.strategy_selection.submission.selected : null,
      families: (Array.isArray(shadow?.coverage?.families) ? shadow.coverage.families : [])
        .filter(f => f && typeof f.family_id === 'string' && typeof f.coverage_state === 'string')
        .map(f => ({ id: f.family_id, state: f.coverage_state })),
      strategies: strategies.map(s => ({
        id: s.strategy_id, name: displayName(s.strategy_id, STRATEGY_NAMES), confidence: s.confidence,
      })),
      techniques: techniques.map(t => ({
        id: t.technique_id, name: displayName(t.technique_id, TECHNIQUE_NAMES),
        confidence: t.presence_confidence,
      })),
      satisfactionScore: confirmed?.confidence ?? null,
      authorityTier: outcome?.authority_tier ?? '',
      elapsedMs: typeof shadow?.elapsed_ms === 'number' && Number.isFinite(shadow.elapsed_ms) ? shadow.elapsed_ms : 0,
      extractorVersion: shadow?.extractor_version ?? '',
      factCount: outcome?.fact_count ?? (Array.isArray(shadow?.structural_facts) ? shadow.structural_facts.length : 0),
      reasoning: Array.isArray(outcome?.reasoning) ? outcome.reasoning : [],
    },
  }
}
