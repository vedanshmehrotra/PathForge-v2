export interface AnalyzeRequest {
  user_id: string
  code: string
  language?: string
}

export interface AnalyzeResponse {
  ast: Record<string, unknown>
  match_result: Record<string, unknown>
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
  summary: Record<string, unknown>
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
    topic: string
    elo_rating: number
    peak_elo: number
    samples: number
    confidence: number
  }>
  overall_elo: number
}
