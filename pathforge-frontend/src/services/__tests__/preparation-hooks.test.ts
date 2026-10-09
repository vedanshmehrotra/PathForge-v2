import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAnalyzeCode, usePrepareProblem } from '../../hooks/useApi'
import { analyzeCode, prepareProblem } from '../api/endpoints'
import { ApiError } from '../api/client'

// Stateful hook doubles let async requests settle without a DOM or real API.
const state = vi.hoisted(() => ({ values: [] as unknown[], refs: [] as { current: number }[], index: 0, refIndex: 0 }))
vi.mock('react', () => ({
  useState: (initial: unknown) => {
    const index = state.index++
    if (!(index in state.values)) state.values[index] = initial
    return [state.values[index], (value: unknown) => { state.values[index] = value }]
  },
  useRef: (initial: number) => {
    const index = state.refIndex++
    if (!(index in state.refs)) state.refs[index] = { current: initial }
    return state.refs[index]
  },
  useCallback: (callback: unknown) => callback,
  useEffect: vi.fn(),
}))
vi.mock('@/services/api/endpoints', () => ({
  analyzeCode: vi.fn(), prepareProblem: vi.fn(), fetchGaps: vi.fn(), fetchElo: vi.fn(), fetchRecommendations: vi.fn(),
}))
vi.mock('@/services/api/auth', () => ({ fetchAuthProfile: vi.fn() }))

const prepared = { leetcode_id: 209, title_slug: 'minimum-size-subarray-sum', title: 'Fixture', difficulty: 'Medium', topics: [] }
function render<T>(hook: () => T): T {
  state.index = state.refIndex = 0
  return hook()
}
function pending<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(done => { resolve = done })
  return { promise, resolve }
}
beforeEach(() => {
  state.values = []
  state.refs = []
  vi.resetAllMocks()
})

describe('explicit preparation and analysis retry', () => {
  it('preserves the preparation-required message/code without automatically preparing', async () => {
    vi.mocked(analyzeCode).mockRejectedValue(new ApiError(409, 'Prepare first.', { detail: { code: 'PREPARATION_REQUIRED' } }))
    await render(useAnalyzeCode).run({ user_id: 7, code: 'pass', problem: { leetcode_id: 209 } })
    expect(render(useAnalyzeCode)).toMatchObject({ result: null, loading: false, error: 'Prepare first.', errorCode: 'PREPARATION_REQUIRED' })
    expect(prepareProblem).not.toHaveBeenCalled()
    vi.mocked(analyzeCode).mockResolvedValue({ ast: {}, match_result: {} })
    await render(useAnalyzeCode).run({ user_id: 7, code: 'pass' })
    expect(render(useAnalyzeCode)).toMatchObject({ error: null, errorCode: null, loading: false })
  })

  it('prepares numeric identifiers only when explicitly requested', async () => {
    vi.mocked(prepareProblem).mockResolvedValue(prepared)
    const hook = render(usePrepareProblem)
    expect(prepareProblem).not.toHaveBeenCalled()
    await hook.run('209')
    expect(prepareProblem).toHaveBeenCalledExactlyOnceWith({ problem: { leetcode_id: 209 } })
    expect(render(usePrepareProblem).result).toEqual(prepared)
  })

  it('preserves URL/slug preparation', async () => {
    vi.mocked(prepareProblem).mockResolvedValue(prepared)
    await render(usePrepareProblem).run('https://leetcode.com/problems/two-sum/')
    expect(prepareProblem).toHaveBeenCalledWith({ problem: { title_slug: 'two-sum' } })
  })

  it('does not mark failed preparation ready or retry automatically', async () => {
    vi.mocked(prepareProblem).mockRejectedValue(new ApiError(409, 'Preparation unavailable.', { detail: { code: 'GROUND_TRUTH_UNAVAILABLE' } }))
    await render(usePrepareProblem).run('209')
    expect(render(usePrepareProblem)).toMatchObject({ result: null, loading: false, error: 'Preparation unavailable.' })
    expect(prepareProblem).toHaveBeenCalledTimes(1)
  })

  it('ignores a preparation response after input invalidation', async () => {
    const reply = pending<typeof prepared>()
    vi.mocked(prepareProblem).mockReturnValue(reply.promise)
    const hook = render(usePrepareProblem)
    const request = hook.run('209')
    hook.clear()
    reply.resolve(prepared)
    await request
    expect(render(usePrepareProblem)).toMatchObject({ result: null, error: null, loading: false })
  })

  it('does not let an older preparation overwrite a newer one', async () => {
    const old = pending<typeof prepared>()
    const newer = { ...prepared, leetcode_id: 121, title: 'Newer fixture' }
    vi.mocked(prepareProblem).mockReturnValueOnce(old.promise).mockResolvedValueOnce(newer)
    const hook = render(usePrepareProblem)
    const olderRequest = hook.run('209')
    await hook.run('121')
    old.resolve(prepared)
    await olderRequest
    expect(render(usePrepareProblem)).toMatchObject({ result: newer, loading: false })
  })
})
