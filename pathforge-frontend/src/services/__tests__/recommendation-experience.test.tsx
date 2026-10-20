import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import type { RecommendResponse } from '../../types/api'
import { RecommendationsView } from '../../../components/recommendations-view'
import { RecommendedPreview } from '../../../components/dashboard'
import { AppShell } from '../../../components/app-shell'

const fixture = vi.hoisted(() => ({
  data: null as RecommendResponse | null, loading: false, error: null as string | null, refresh: vi.fn(),
}))
vi.mock('@/hooks/useApi', () => ({ useRecommendations: () => fixture }))
vi.mock('@/hooks/usePracticeSkips', () => ({ usePracticeSkips: () => ({
  ready: true, excludedIds: [], skip: vi.fn(), reset: vi.fn(),
}) }))
vi.mock('@/auth/AuthProvider', () => ({ useAuth: () => ({
  user: { id: 'local-fixture' }, profile: { user_id: 7 }, loading: false, signOut: vi.fn(),
}) }))
vi.mock('next/navigation', () => ({ usePathname: () => '/recommendations' }))
vi.mock('@/components/login-screen', () => ({ LoginScreen: () => null }))

const response: RecommendResponse = {
  recommendations: [{problem_id:'1',title:'Two Sum',difficulty:'Easy',pattern:'hash_map_lookup',
    reason:'Significant weakness detected in hash map lookup.',score:75,
    problem_url:'https://leetcode.com/problems/two-sum/'}],
  summary: {primary_weak_patterns:['hash_map_lookup'],focus_area:'Arrays',recommendation_strategy:'reinforce_weakest'},
}
const render = (component = RecommendationsView) => renderToStaticMarkup(createElement(component))

beforeEach(() => { fixture.data = structuredClone(response); fixture.loading = false; fixture.error = null })

describe('recommendation usability without unsupported diagnosis claims', () => {
  it('offers a real problem destination without presenting heuristic scores as learning gains', () => {
    const html = render()
    expect(html).toContain('href="https://leetcode.com/problems/two-sum/"')
    expect(html).toContain('Open on LeetCode')
    expect(html).not.toMatch(/expected gain|EST. TOTAL GAIN|maximize Elo|Significant weakness/i)
  })

  it('distinguishes service errors from an empty list and offers retry', () => {
    fixture.error = 'Recommendation service unavailable'
    const html = render()
    expect(html).toContain('role="alert"')
    expect(html).toContain(fixture.error)
    expect(html).toContain('Retry')
    expect(html).not.toContain('Two Sum')
    expect(html).not.toContain('Submit code to generate')
  })

  it('gives an honest empty state without requiring an analysis submission', () => {
    fixture.data!.recommendations = []
    const html = render()
    expect(html).toContain('No practice suggestions are available')
    expect(html).toContain('Refresh suggestions')
    expect(html).not.toContain('Submit code to generate')
  })

  it('does not render stale cards during loading', () => {
    fixture.loading = true
    expect(render()).not.toContain('Two Sum')
  })

  it('keeps missing destinations explicit rather than inventing a slug from an internal ID', () => {
    delete fixture.data!.recommendations[0].problem_url
    const html = render()
    expect(html).toContain('Problem link unavailable')
    expect(html).not.toContain('Open on LeetCode')
  })

  it('does not render duplicate cards for the same problem', () => {
    fixture.data!.recommendations.push({...fixture.data!.recommendations[0]})
    expect(render().match(/>Two Sum<\/h2>/g)).toHaveLength(1)
  })

  it('uses the same conservative destination and error behavior on the dashboard', () => {
    const html = render(RecommendedPreview)
    expect(html).toContain('href="https://leetcode.com/problems/two-sum/"')
    expect(html).not.toMatch(/expected gain|Significant weakness/i)
    fixture.error = 'Could not load suggestions'
    expect(render(RecommendedPreview)).toContain(fixture.error)
    expect(render(RecommendedPreview)).toContain('Retry')
  })

  it('shows provenance-qualified practice reasons without old weakness claims', () => {
    fixture.data!.policy = 'recorded_practice_v1'
    const item = fixture.data!.recommendations[0]
    item.practice_kind = 'revisit'
    item.reason = 'Revisit a previously recorded problem; it is older than your latest recorded problem.'
    item.topics = ['Array', 'Hash Table']
    expect(render()).toContain(item.reason)
    expect(render()).toContain('Catalog topics: Array, Hash Table')
    expect(render()).toContain('aria-label="Skip Two Sum"')
    expect(render(RecommendedPreview)).toContain(item.reason)
  })

  it('makes bounded and unmapped history limitations visible', () => {
    fixture.data!.policy = 'recorded_practice_v1'
    fixture.data!.history = { scope: 'latest_recorded_submissions', limit: 1000,
      truncated: true, mapped_problems: 2, unmapped_submissions: 3 }
    expect(render()).toContain('older practice may not be represented')
    expect(render()).toContain('could not be linked to the current bank')
  })

  it('presents calendar roles and factual reasons without ability claims', () => {
    fixture.data!.policy = 'calendar_practice_v2'
    fixture.data!.recommendations[0] = {...fixture.data!.recommendations[0], practice_kind: 'related_return',
      pattern: '', score: null, reason: 'Shares Hash Table with Two Sum, recorded on 2026-10-10.'}
    const html = render()
    expect(html).toContain('Return to a topic')
    expect(html).toContain('recorded on 2026-10-10')
    expect(html).toContain('practice saved with a problem selected')
    expect(html).toContain('aria-label="Skip Two Sum"')
    expect(render(RecommendedPreview)).toContain('Return to a topic')
    expect(html).not.toMatch(/Significant weakness|mastered|learning gain|role="progressbar"/i)
  })

  it('discloses missing dates without inventing a return schedule', () => {
    fixture.data!.policy = 'calendar_practice_v2'
    fixture.data!.history = {scope: 'latest_recorded_submissions', limit: 1000,
      truncated: false, mapped_problems: 1, unmapped_submissions: 0, invalid_timestamps: 1}
    expect(render()).toContain('Some practice dates are unavailable')
  })

  it.each([
    ['session_exhausted', 'Reset skips'], ['caught_up', 'bring a problem of your own'],
    ['no_candidates', 'for this difficulty'],
  ] as const)('explains %s instead of inventing a recommendation', (state, message) => {
    fixture.data!.recommendations = []
    fixture.data!.state = state
    expect(render()).toContain(message)
  })

  it('provides mobile navigation without claiming unmeasured backend health', () => {
    const html = renderToStaticMarkup(createElement(AppShell, null, 'Local content'))
    expect(html).toContain('aria-label="Mobile navigation"')
    expect(html).not.toContain('engine live')
  })
})
