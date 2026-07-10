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

export interface ProblemInfo {
  leetcode_id?: number | null
  title?: string | null
  difficulty?: string | null
  canonical_patterns: CanonicalPattern[]
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
  }
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
}

export interface RecommendResponse {
  recommendations: Array<{
    problem_id: string
    title: string
    difficulty: string
    pattern: string
    reason: string
    score: number
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
