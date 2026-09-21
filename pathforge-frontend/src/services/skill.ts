/**
 * Shared presentation helpers for pattern Elo.
 *
 * These thresholds are display-only bands used consistently across the
 * dashboard and the Learning Progress page. They do not affect any engine.
 */

export const STRONG_ELO = 1800
export const DEVELOPING_ELO = 1650
export const ELO_METER_MAX = 2200

export type SkillStatus = 'Strong' | 'Developing' | 'Needs practice'

export function skillStatus(elo: number): SkillStatus {
  if (elo >= STRONG_ELO) return 'Strong'
  if (elo >= DEVELOPING_ELO) return 'Developing'
  return 'Needs practice'
}

export function statusVariant(status: SkillStatus): 'success' | 'accent' | 'warning' {
  if (status === 'Strong') return 'success'
  if (status === 'Developing') return 'accent'
  return 'warning'
}

export interface PatternSkill {
  id: string
  /** Human-readable pattern name. */
  name: string
  elo: number
  status: SkillStatus
}
