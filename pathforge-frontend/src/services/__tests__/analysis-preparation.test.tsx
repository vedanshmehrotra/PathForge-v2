import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AnalysisView } from '../../../components/analysis-view'

const fixture = vi.hoisted(() => ({
  input: '', stateIndex: 0, errorCode: null as string | null,
  prepared: null as null | { leetcode_id: number; title: string; difficulty: string },
  preparing: false, run: vi.fn(), clear: vi.fn(), prepare: vi.fn(), effects: [] as (() => void)[],
}))
vi.mock('react', async importOriginal => ({
  ...await importOriginal<typeof import('react')>(),
  useState: () => [fixture.stateIndex++ === 0 ? 'def solve(): return 1' : fixture.input, vi.fn()],
  useEffect: (callback: () => void) => { fixture.effects.push(callback) },
}))
vi.mock('@/auth/AuthProvider', () => ({ useAuth: () => ({ profile: { user_id: 7 } }) }))
vi.mock('@/hooks/useApi', () => ({
  useAnalyzeCode: () => ({ result: null, loading: false, error: null, errorCode: fixture.errorCode, run: fixture.run }),
  usePrepareProblem: () => ({ result: fixture.prepared, loading: fixture.preparing, error: null, run: fixture.prepare, clear: fixture.clear }),
  useGapData: () => ({ data: null }),
}))

type Element = { type: unknown; props: { children?: unknown; disabled?: boolean; onClick?: () => void; onChange?: (event: { target: { value: string } }) => void; placeholder?: string } }
function elements(node: unknown): Element[] {
  if (Array.isArray(node)) return node.flatMap(elements)
  if (!node || typeof node !== 'object' || !('props' in node)) return []
  const element = node as Element
  return [element, ...elements(element.props.children)]
}
function render() {
  fixture.stateIndex = 0
  const nodes = elements(AnalysisView())
  const run = nodes.find(node => node.type === 'button' && Array.isArray(node.props.children) && node.props.children.includes('Run Analysis'))!
  const input = nodes.find(node => node.type === 'input' && node.props.placeholder?.includes('LeetCode'))!
  return { run, input }
}
beforeEach(() => {
  fixture.input = ''
  fixture.prepared = null
  fixture.preparing = false
  fixture.errorCode = null
  fixture.effects = []
  vi.clearAllMocks()
})

describe('analysis preparation UI guards', () => {
  it('preserves intentional analysis without a problem', () => {
    const { run } = render()
    expect(run.props.disabled).toBe(false)
    run.props.onClick!()
    expect(fixture.run).toHaveBeenCalledExactlyOnceWith({ user_id: 7, code: 'def solve(): return 1', language: 'python' })
  })

  it('blocks typed but unprepared identifiers, including direct handler invocation', () => {
    fixture.input = '209'
    const { run } = render()
    expect(run.props.disabled).toBe(true)
    run.props.onClick!()
    expect(fixture.run).not.toHaveBeenCalled()
    expect(fixture.prepare).not.toHaveBeenCalled()
  })

  it('sends the prepared identifier', () => {
    fixture.input = '209'
    fixture.prepared = { leetcode_id: 209, title: 'Fixture', difficulty: 'Medium' }
    const { run } = render()
    expect(run.props.disabled).toBe(false)
    run.props.onClick!()
    expect(fixture.run.mock.calls[0][0].problem).toEqual({ leetcode_id: 209 })
  })

  it('invalidates preparation when editing input while a request is pending', () => {
    fixture.input = '209'
    fixture.preparing = true
    const { run, input } = render()
    expect(run.props.disabled).toBe(true)
    input.props.onChange!({ target: { value: '121' } })
    expect(fixture.clear).toHaveBeenCalledOnce()
  })

  it.each(['PREPARATION_REQUIRED', 'GROUND_TRUTH_UNAVAILABLE'])('clears stale readiness on %s without automatic preparation', code => {
    fixture.errorCode = code
    render()
    fixture.effects.forEach(effect => effect())
    expect(fixture.clear).toHaveBeenCalledOnce()
    expect(fixture.prepare).not.toHaveBeenCalled()
  })
})
