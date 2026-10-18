/** Render actual resolver/engine/API output; mocked transport is not a diagnosis. */
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { ApproachComparison } from '../../../components/approach-comparison'
import { ExperimentalPanel } from '../../../components/experimental-panel'
import { AnalysisView } from '../../../components/analysis-view'
import type { AnalyzeResponse } from '../../types/api'

const fixture = vi.hoisted(() => ({ response: null as AnalyzeResponse | null }))
vi.mock('@/auth/AuthProvider', () => ({ useAuth: () => ({ profile: { user_id: 7 } }) }))
vi.mock('@/hooks/useApi', () => ({
  useAnalyzeCode: () => ({ result: fixture.response, loading: false, error: null, errorCode: null, run: vi.fn() }),
  usePrepareProblem: () => ({ result: null, loading: false, error: null, run: vi.fn(), clear: vi.fn() }),
  useGapData: () => ({ data: null }),
}))

let cases: Record<string, { code: string; response: AnalyzeResponse }>
beforeAll(() => {
  const output = execFileSync(process.env.PATHFORGE_TEST_PYTHON || 'python',
    ['-B', '-X', 'utf8', '-m', 'pathforge.tests.test_approach_family_contract'],
    { cwd: path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..'),
      encoding: 'utf8', maxBuffer: 2 * 1024 * 1024 })
  cases = JSON.parse(output)
}, 30000)

function render(name: string): string {
  const info = cases[name].response.problem_info
  return renderToStaticMarkup(createElement(ApproachComparison, {
    groups: info?.solution_groups, legacyPatterns: info?.canonical_patterns,
  }))
}

describe('consistent approach presentation using real engine/API results', () => {
  it('explains a proposed approach with all listed patterns observed without promoting it', () => {
    const html = render('tentative')
    expect(html).toContain('Listed patterns observed — proposed approach')
    expect(html).toContain('Tentative comparison')
    expect(html).not.toContain('Pattern alignment observed')
    expect(html).not.toContain('Inconclusive comparison')
    expect(html).toContain('does not establish a confirmed strategy')
  })

  it('shows a reviewed alignment without claiming all alternatives are required', () => {
    const html = render('fixed_alternative')
    expect(html).toContain('Pattern alignment observed')
    expect(html).toContain('Unused alternative')
    expect(html).toContain('This alternative is not required')
    expect(html).toContain('Prefix differences')
    expect(html).not.toMatch(/skill deficit|All expected patterns detected|[0-9]+% match/)
  })

  it('preserves combined requirements and explains incomplete evidence', () => {
    const html = render('composite_partial')
    expect(html).toContain('Inconclusive comparison')
    expect(html).toContain('combined requirements')
    expect(html).toContain('Stored expectation')
    expect(html).toContain('Detected evidence')
    expect(html).toMatch(/prefix sum<\/th><td[^>]*>Not observed/)
    expect(html).toMatch(/hash map lookup<\/th><td[^>]*>Observed/)
    expect(html).not.toContain('Pattern alignment observed')
  })

  it.each(['legacy_ambiguous', 'nesting_depth', 'malformed_relation', 'incomplete_relation'])('keeps %s tentative regardless of legacy verdict', name => {
    const html = render(name)
    expect(html).toContain('Tentative comparison')
    expect(html).toContain('Inconclusive comparison')
    expect(html).not.toContain('Pattern alignment observed')
  })

  it('keeps missing or older metadata conservative', () => {
    const html = renderToStaticMarkup(createElement(ApproachComparison, {
      legacyPatterns: [{ name: 'sliding_window_fixed', confidence: 0.95 }],
    }))
    expect(html).toContain('Comparison unavailable')
    expect(html).toContain('relationship unverified')
    expect(html).not.toContain('95%')
  })

  it('does not elevate old, contradictory or conflicting proposed payloads', () => {
    const source = cases.tentative.response.problem_info!.solution_groups![0]
    for (const change of [
      { pattern_evidence_state: undefined },
      { observed_patterns: [] },
      { review_state: 'CONFLICT' as const },
      { pattern_evidence_state: 'UNAVAILABLE' as const },
    ]) {
      const html = renderToStaticMarkup(createElement(ApproachComparison, { groups: [{ ...source, ...change }] }))
      expect(html).toContain('Inconclusive comparison')
      expect(html).not.toContain('Listed patterns observed — proposed approach')
    }
  })

  it('keeps an unmatched proposed alternative out of a universal checklist', () => {
    const groups = structuredClone(cases.fixed_alternative.response.problem_info!.solution_groups!)
    groups.forEach(group => { group.review_state = 'UNREVIEWED'; group.authority_tier = 'llm_proposed' })
    const html = renderToStaticMarkup(createElement(ApproachComparison, { groups }))
    expect(html).toContain('Other proposed alternative')
    expect(html).toContain('Other proposed option')
    expect(html).not.toContain('Not required')
    expect(html).not.toContain('Pattern alignment observed')
  })

  it('does not promote technique alignment into a canonical strategy', () => {
    expect(render('lookup')).toContain('Pattern alignment observed')
    const html = renderToStaticMarkup(createElement(ExperimentalPanel, { shadowAnalysis: cases.lookup.response.shadow_analysis }))
    expect(html).toContain('Not enough evidence')
    expect(html).not.toContain('Observed strategy')
  })

  it('rejects inconsistent claimed full comparisons', () => {
    const groups = structuredClone(cases.fixed_alternative.response.problem_info!.solution_groups!)
    groups[0].observed_patterns = []
    const html = renderToStaticMarkup(createElement(ApproachComparison, { groups }))
    expect(html).not.toContain('Pattern alignment observed')
    expect(html).toContain('Inconclusive comparison')
  })

  it.each(['fixed_alternative', 'composite_partial', 'tentative', 'legacy_ambiguous', 'nesting_depth', 'no_problem'])
    ('the full analysis view avoids misleading verdicts for %s', name => {
      fixture.response = cases[name].response
      const html = renderToStaticMarkup(createElement(AnalysisView))
      expect(html).toContain('Detected in your code')
      expect(html).toContain('Approach Comparison')
      expect(html).not.toMatch(/No expected patterns detected|Some expected patterns missing|All expected patterns detected|Submission Gap/)
      if (name !== 'fixed_alternative') expect(html).not.toContain('Pattern alignment observed')
    })
})
