import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { DashboardView } from '../../../components/dashboard'
import { ProgressView } from '../../../components/progress-view'
import { ProfileView } from '../../../components/profile-view'
import { LoginScreen } from '../../../components/login-screen'

const fixture = vi.hoisted(() => ({
  profiles: [] as Array<Record<string, unknown>>, ratings: {} as Record<string, number>,
  error: null as string | null, confirmedAt: undefined as string | undefined,
  refresh: vi.fn(),
  practiceRecords: undefined as Array<Record<string, unknown>> | undefined,
  levels: {} as Record<string, Record<string, number>>,
  loaded: true, loading: false,
}))
vi.mock('@/auth/AuthProvider', () => ({ useAuth: () => ({ profile: { user_id: 7, display_name: 'Learner' },
  user: { email: 'fixture@example.invalid', email_confirmed_at: fixture.confirmedAt, app_metadata: { provider: 'google' } }, signOut: vi.fn(),
}) }))
vi.mock('@/auth/authService', () => ({ signInWithGoogle: vi.fn() }))
vi.mock('@/hooks/useApi', () => ({
  useAuthProfile: () => ({ data: fixture.loaded ? { profiles: fixture.profiles, practice_records: fixture.practiceRecords } : null, loading: fixture.loading, error: fixture.error, refresh: fixture.refresh }),
  useEloData: () => ({ data: fixture.loaded ? { pattern_elo: fixture.ratings, pattern_levels: fixture.levels } : null, loading: fixture.loading, error: fixture.error, refresh: fixture.refresh }),
  useRecommendations: () => ({ data: null, loading: false, error: null, refresh: fixture.refresh }),
}))
const render = (component: typeof DashboardView) => renderToStaticMarkup(createElement(component))
beforeEach(() => {
  fixture.profiles = []
  fixture.ratings = {}
  fixture.error = null
  fixture.confirmedAt = undefined
  fixture.practiceRecords = undefined
  fixture.levels = {}
  fixture.loaded = true
  fixture.loading = false
})

describe('a practice workspace without unsupported proficiency claims', () => {
  it('uses recent saved practice even when the scoring profile is a month old', () => {
    fixture.profiles = [{ topic: 'array_traversal', attempt_count: 4, accuracy: .5, last_attempt_at: '2026-09-01T00:00:00Z' }]
    fixture.practiceRecords = [{ topic: 'array_traversal', attempt_count: 5, last_attempt_at: new Date().toISOString() }]
    const html = render(ProgressView)
    expect(html).toContain('Last recorded today')
    expect(html).toContain('A level appears after an eligible, verified comparison')
    expect(html).toContain('Your recent practice')
    expect(render(DashboardView)).toContain('today')
  })

  it('shows the server-derived pattern level and progress without inventing XP', () => {
    fixture.ratings = { hash_map_lookup: 1232 }
    fixture.levels = { hash_map_lookup: { level: 5, experience: 832, into_level: 32, points_per_level: 200, progress_percent: 16 } }
    const html = render(ProgressView)
    expect(html).toContain('Level 5')
    expect(html).toContain('32 / 200 XP')
    expect(html).toContain('progress toward level 6')
    expect(html).toContain('XP and levels can rise or fall')
  })
  it('gives a new learner a starting action without an empty ratings dashboard', () => {
    const html = render(DashboardView)
    expect(html).toContain('Start with a solution you know.')
    expect(html).toContain('Analyze a solution')
    expect(html).not.toMatch(/Average Elo|Needs Practice|Skill Snapshot|role="progressbar"/)
  })

  it('uses recorded activity rather than converting ratings into learner diagnoses', () => {
    fixture.ratings = { sliding_window_fixed: 1420, hash_map_lookup: 980 }
    fixture.profiles = [{ topic: 'sliding_window_fixed', attempt_count: 12, last_attempt_at: null }]
    const html = render(DashboardView)
    expect(html).toContain('sliding window fixed')
    expect(html).toContain('Recorded previously')
    expect(html).not.toMatch(/1420|980|confirmed|accuracy|Needs practice|Stronger Areas/)
  })

  it('does not disguise a history service failure as no practice', () => {
    fixture.error = 'Fixture unavailable'
    fixture.loaded = false
    const html = render(DashboardView)
    expect(html).toContain('role="alert"')
    expect(html).toContain('Retry history')
    expect(html).not.toContain('Your recorded patterns will appear here')
    expect(render(ProgressView)).toContain('Retry history')
  })

  it('preserves loaded history and levels when a later refresh fails', () => {
    fixture.profiles = [{ topic: 'array_traversal', attempt_count: 4, last_attempt_at: new Date().toISOString() }]
    fixture.ratings = { array_traversal: 1232 }
    fixture.levels = { array_traversal: { level: 5, experience: 832, into_level: 32, points_per_level: 200, progress_percent: 16 } }
    fixture.error = 'Temporary network failure'
    const dashboard = render(DashboardView)
    expect(dashboard).toContain('Could not refresh practice history')
    expect(dashboard).toContain('Take another look at how you solve.')
    expect(dashboard).toContain('array traversal')
    const progress = render(ProgressView)
    expect(progress).toContain('Could not refresh progress')
    expect(progress).toContain('Showing the last loaded data')
    expect(progress).toContain('Level 5')
    expect(progress).toContain('Recorded patterns')
    expect(progress).not.toContain('Could not load your practice history')
  })

  it('keeps loaded progress visible while a deliberate retry is in flight', () => {
    fixture.profiles = [{ topic: 'array_traversal', attempt_count: 4 }]
    fixture.loading = true
    expect(render(DashboardView)).toContain('array traversal')
    expect(render(ProgressView)).toContain('Recorded patterns')
    expect(render(ProgressView)).not.toContain('Loading your practice history')
  })

  it('lets learners choose a recorded focus without contradictory strength bands', () => {
    fixture.ratings = { sliding_window_fixed: 1420, hash_map_lookup: 980 }
    const html = render(ProgressView)
    expect(html).toContain('Choose your own focus')
    expect(html).toContain('This list is alphabetical')
    expect(html).toContain('Recorded metrics')
    expect(html).toContain('Rating history is not retained')
    expect(html).not.toMatch(/Stronger Areas|Needs practice|below average|rating movement will appear/)
    expect(html.indexOf('hash map lookup')).toBeLessThan(html.indexOf('sliding window fixed'))
  })

  it('does not assert email verification when the session provides no evidence', () => {
    expect(render(ProfileView)).toContain('Verification not confirmed')
    expect(render(ProfileView)).not.toContain('Email verified')
    fixture.confirmedAt = '2026-10-16T00:00:00Z'
    expect(render(ProfileView)).toContain('Email verified')
  })

  it('illustrates the product without invented gains or strategy confirmation', () => {
    const html = render(LoginScreen)
    expect(html).toContain('Illustrative Python snippet')
    expect(html).not.toMatch(/\+18|\+25|\+24|confirmed solve|approach identified|CONFIRMED/)
    expect(html).toContain('does not execute code')
  })
})
