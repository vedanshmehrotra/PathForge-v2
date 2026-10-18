import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AnalysisView } from '../../../components/analysis-view'

const fixture = vi.hoisted(() => ({
  stateIndex: 0, values: [] as unknown[], effects: [] as (() => void)[],
  error: 'Old problem comparison unsupported.', errorCode: 'COMPARISON_UNSUPPORTED' as string | null,
  clear: vi.fn(),
}))
vi.mock('react', async importOriginal => ({
  ...await importOriginal<typeof import('react')>(),
  useState: () => [fixture.values[fixture.stateIndex++], vi.fn()],
  useRef: (current: unknown) => ({ current }),
  useEffect: (effect: () => void) => { fixture.effects.push(effect) },
}))
vi.mock('@/auth/AuthProvider', () => ({ useAuth: () => ({ profile: { user_id: 7 } }) }))
vi.mock('@/hooks/useApi', () => ({
  useAnalyzeCode: () => ({ result: null, loading: false, error: fixture.error, errorCode: fixture.errorCode, run: vi.fn() }),
  usePrepareProblem: () => ({ result: { leetcode_id: 121, title: 'New problem' }, loading: false,
    error: null, unsupported: null, clear: fixture.clear, run: vi.fn() }),
}))
type Element = { type: unknown; props: { children?: unknown } }
function elements(node: unknown): Element[] {
  if (Array.isArray(node)) return node.flatMap(elements)
  if (!node || typeof node !== 'object' || !('props' in node)) return []
  const element = node as Element
  return [element, ...elements(element.props.children)]
}
beforeEach(() => {
  fixture.stateIndex = 0
  fixture.effects = []
  fixture.values = ['pass', '121', false, { code: 'pass', problem: '209', problemId: 209 }]
  fixture.errorCode = 'COMPARISON_UNSUPPORTED'
  vi.clearAllMocks()
})
describe('analysis errors belong to the submitted inputs', () => {
  it.each(['COMPARISON_UNSUPPORTED', 'GROUND_TRUTH_UNAVAILABLE', 'PREPARATION_REQUIRED'])('does not clear a new preparation on a stale %s response', code => {
    fixture.errorCode = code
    const nodes = elements(AnalysisView())
    fixture.effects.forEach(effect => effect())
    expect(fixture.clear).not.toHaveBeenCalled()
    expect(JSON.stringify(nodes.map(node => node.props.children))).not.toContain('Old problem comparison unsupported.')
    expect(nodes.some(node => node.type === 'button' && node.props.children === 'Inspect code only')).toBe(false)
  })
  it('hides an old error after the source code changes', () => {
    fixture.values = ['print(1)', '209', false, { code: 'pass', problem: '209', problemId: 209 }]
    const nodes = elements(AnalysisView())
    fixture.effects.forEach(effect => effect())
    expect(fixture.clear).not.toHaveBeenCalled()
    expect(JSON.stringify(nodes.map(node => node.props.children))).not.toContain('Old problem comparison unsupported.')
  })
})
