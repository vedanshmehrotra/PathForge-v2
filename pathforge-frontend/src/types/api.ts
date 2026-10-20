export interface AnalyzeRequest {
  user_id: number
  code: string
  language?: string
  problem?: {
    leetcode_id?: number
    title_slug?: string
  }
}

export interface CanonicalPattern {
  name: string
  confidence: number
}

export interface SolutionApproach {
  id: string
  name: string
  patterns: string[]
  required: string[]
  optional: string[]
  excluded: string[]
  family_relation?: string | null
  alternative_group_id?: string | null
  provenance: string[]
  authority_tier?: string | null
  definition_state: 'EXPLICIT' | 'LEGACY_UNSPECIFIED'
  review_state: 'REVIEWED' | 'UNREVIEWED' | 'CONFLICT'
  comparison_state: 'FULL_MATCH' | 'PARTIAL_MATCH' | 'NO_MATCH' | 'NOT_EVALUATED'
  pattern_evidence_state?: 'NOT_EVALUATED' | 'ALL_OBSERVED' | 'SOME_OBSERVED' | 'NONE_OBSERVED' | 'UNAVAILABLE'
  observed_patterns: string[]
  unobserved_patterns: string[]
  limitations: string[]
}

export interface UnscoredApproach {
  id: string
  name: string
  description: string
  coverage_limit: string
  comparison_support: 'UNSUPPORTED'
  patterns: string[]
  contract_version: 2
  source_sha256: string
  provenance: string[]
  authority_tier: 'llm_proposed'
}

export interface ProblemInfo {
  leetcode_id?: number | null
  title?: string | null
  difficulty?: string | null
  canonical_patterns: CanonicalPattern[]
  solution_groups?: SolutionApproach[]
  unscored_approaches?: UnscoredApproach[]
  ground_truth_consistency?: Record<string, unknown>[]
}

export interface EloUpdate {
  pattern_id: string
  elo_before: number
  elo_after: number
  delta: number
}

export interface SubmissionGap {
  detected_pattern_ids: string[]
  missing_pattern_ids: string[]
  gap_identified: boolean
}

export interface ShadowMatchOutcome {
  outcome: 'CONFIRMED' | 'UNRESOLVED' | 'CONTRADICTED'
  satisfied_group_ids: string[]
  authority_tier: string
  primary_strategy: string | null
  reasoning: string[]
  technique_count: number
  strategy_count: number
  fact_count: number
}

export interface ShadowAnalysisResult {
  structural_facts: Record<string, unknown>[]
  technique_evidence: Array<{
    technique_id: string
    technique_version: string
    supporting_fact_ids: string[]
    presence_confidence: number
    centrality: number
  }>
  strategy_evidence: Array<{
    strategy_id: string
    strategy_version: string
    supporting_technique_ids: string[]
    supporting_fact_ids: string[]
    confidence: number
    problem_context_signals: Record<string, unknown>
  }>
  match_outcome?: ShadowMatchOutcome | null
  coverage?: {
    no_ground_truth: boolean
    aggregate_state: string
    families: Array<{
      family_id: string
      coverage_state: 'CONFIRMED' | 'PROVISIONAL' | 'UNRESOLVED' | 'CONTRADICTED' | 'UNMATCHABLE'
      conclusion_eligible_present: string[]
    }>
  } | null
  strategy_selection?: {
    submission: ShadowStrategySelection
    families: ShadowStrategySelection[]
  } | null
  extractor_version: string
  elapsed_ms: number
}

export interface ShadowStrategySelection {
  scope: 'submission' | 'family'
  family_id: string | null
  selected: string | null
  ambiguity: boolean
  tie_resolved: boolean
  reason_codes: string[]
  candidates: Array<{
    concept_id: string
    confidence: number
    specificity_rank: number
    tier: string
    evidence_source: string
  }>
}

export interface AnalyzeResponse {
  ast: Record<string, unknown>
  match_result: Record<string, unknown>
  problem_info?: ProblemInfo | null
  elo_updates?: EloUpdate[]
  submission_gap?: SubmissionGap | null
  persisted?: {
    submission_id: number
    gap_signals_count: number
    elo_updates_count: number
    recommendation_id?: number | null
    skill_updates_skipped?: boolean | null
  }
  shadow_analysis?: ShadowAnalysisResult | null
}

export interface PrepareRequest {
  problem: {
    leetcode_id?: number
    title_slug?: string
  }
}

export interface PrepareResponse {
  leetcode_id: number
  title_slug: string
  title: string
  difficulty: string
  topics: string[]
  solution_groups?: SolutionApproach[]
  unscored_approaches?: UnscoredApproach[]
}

export interface GapRequest {
  user_id: number
}

export interface GapSignal {
  pattern_id: string
  gap_strength: number
  frequency: number
  last_seen: string
}

export interface GapResponse {
  gap_signals: GapSignal[]
  summary: {
    strong_gaps: string[]
    moderate_gaps: string[]
    weak_gaps: string[]
  }
}

export interface EloRequest {
  user_id: number
}

export interface EloResponse {
  pattern_elo: Record<string, number>
  summary: {
    average_elo: number
    weakest_patterns: string[]
    strongest_patterns: string[]
  }
}

export interface RecommendRequest {
  user_id: number
  mode?: 'legacy' | 'practice'
  policy?: 'recorded_practice_v1' | 'calendar_practice_v2'
  difficulty?: 'Easy' | 'Medium' | 'Hard'
  excluded_ids?: string[]
}

export interface RecommendResponse {
  policy?: 'recorded_practice_v1' | 'calendar_practice_v2'
  state?: 'available' | 'no_candidates' | 'session_exhausted' | 'caught_up'
  history?: {
    scope: 'latest_recorded_submissions'
    limit: number
    truncated: boolean
    mapped_problems: number
    unmapped_submissions: number
    invalid_timestamps?: number
    dated_exposures?: number
    calendar_timezone?: 'UTC'
  }
  limitations?: string[]
  recommendations: Array<{
    problem_id: string
    title: string
    difficulty: string
    pattern: string
    reason: string
    score: number | null
    topics?: string[]
    practice_kind?: 'explore' | 'revisit' | 'related_return' | 'follow_up' | 'starter'
    reason_evidence?: {
      anchor_url: string
      anchor_title: string
      anchor_date: string
      shared_topics: string[]
    }
    /** Validated stored destination; absent in older API responses. */
    problem_url?: string | null
  }>
  summary: {
    primary_weak_patterns: string[]
    focus_area: string
    recommendation_strategy: string
  }
}

export interface UserProfile {
  user_id: number
  username: string
  email: string
  display_name: string
  experience_level: string
  confident_areas: string
  onboarding_complete: boolean
  current_streak: number
  last_submission_date: string | null
  created_at: string
  updated_at: string
}

export interface AuthProfile {
  profiles: Array<{
    user_id: number
    topic: string
    elo_rating: number
    attempt_count: number
    pass_count: number
    pattern_match_count: number
    accuracy: number
    recent_failures: number
    last_attempt_at: string | null
    created_at: string
    updated_at: string
  }>
  overall_elo: number
}
