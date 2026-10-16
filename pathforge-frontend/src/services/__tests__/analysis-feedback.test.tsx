import { beforeAll, describe, expect, it, vi } from 'vitest'
import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { AnalysisEffects } from '../../../components/analysis-effects'
import { AnalysisView } from '../../../components/analysis-view'
import type { AnalyzeResponse } from '../../types/api'

const fixture = vi.hoisted(() => ({ response: null as AnalyzeResponse | null }))
vi.mock('@/auth/AuthProvider', () => ({ useAuth: () => ({ profile: { user_id: 7 } }) }))
vi.mock('@/hooks/useApi', () => ({
  useAnalyzeCode: () => ({ result: fixture.response, loading: false, error: null, errorCode: null, run: vi.fn() }),
  usePrepareProblem: () => ({ result: null, loading: false, error: null, run: vi.fn(), clear: vi.fn() }),
}))

let actual: AnalyzeResponse
beforeAll(() => {
  const output = execFileSync(process.env.PATHFORGE_TEST_PYTHON || 'python',
    ['-B', '-X', 'utf8', '-m', 'pathforge.tests.test_analysis_feedback'],
    { cwd: path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..'), encoding: 'utf8' })
  actual = JSON.parse(output).response
}, 30000)

const effects = (response: AnalyzeResponse) => renderToStaticMarkup(createElement(AnalysisEffects, { result: response }))

describe('concise and truthful analysis feedback', () => {
  it('shows real bracket-case engine output without calling correct code incorrect', () => {
    fixture.response = actual
    const html = renderToStaticMarkup(createElement(AnalysisView))
    expect(html).toContain('Inconclusive comparison')
    expect(html).toContain('Stored expectation')
    expect(html).toContain('Detected evidence')
    expect(html).toContain('monotonic stack')
    expect(html).toContain('array traversal')
    expect(html).toContain('No Elo or gap changes')
    expect(html).toContain('not a code-correctness verdict')
    expect(html).not.toMatch(/your code is incorrect|skill gap increased|Stored history signals/i)
  })

  it('uses the actual persistence skip decision for the no-change claim', () => {
    expect(actual.persisted?.skill_updates_skipped).toBe(true)
    expect(effects(actual)).toContain('No Elo or gap changes')
  })

  it('does not infer skipped scoring from an older payload or an inconclusive comparison', () => {
    const older = structuredClone(actual)
    delete older.persisted!.skill_updates_skipped
    expect(effects(older)).not.toContain('No Elo or gap changes')
    expect(effects(older)).toContain('does not report whether skill updates were skipped')
  })

  it('displays returned Elo deltas, including decreases, without inventing a correctness verdict', () => {
    const scored = structuredClone(actual)
    scored.persisted!.skill_updates_skipped = false
    scored.elo_updates = [
      { pattern_id: 'prefix_sum', elo_before: 1200, elo_after: 1208, delta: 8 },
      { pattern_id: 'hash_map_lookup', elo_before: 1200, elo_after: 1196, delta: -4 },
    ]
    const html = effects(scored)
    expect(html).toContain('+8 Elo')
    expect(html).toContain('-4 Elo')
    expect(html).toContain('prefix sum')
    expect(html).not.toContain('No Elo or gap changes')
  })

  it('does not turn an aggregate gap count into a claim that a gap increased', () => {
    const scored = structuredClone(actual)
    scored.persisted!.skill_updates_skipped = false
    scored.persisted!.gap_signals_count = 2
    expect(effects(scored)).toContain('2 gap signals recorded; change in strength is not reported')
    expect(effects(scored)).not.toMatch(/gap increased|gap decreased/i)
  })

  it('rejects contradictory update metadata instead of asserting no changes', () => {
    const inconsistent = structuredClone(actual)
    inconsistent.persisted!.elo_updates_count = 1
    expect(effects(inconsistent)).toContain('Update details are inconsistent')
    expect(effects(inconsistent)).not.toContain('No Elo or gap changes')
  })
})
