import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthProfile } from '../../hooks/useApi'
import { fetchAuthProfile } from '../api/auth'

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

function render() {
  state.index = state.refIndex = 0
  return useAuthProfile()
}
function pending<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason: Error) => void
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail })
  return { promise, resolve, reject }
}
const record = { profiles: [], practice_records: [{ topic: 'array_traversal', attempt_count: 1,
  last_attempt_at: '2026-10-20T12:00:00+00:00' }], overall_elo: 800 }
beforeEach(() => {
  state.values = []
  state.refs = []
  vi.resetAllMocks()
})

describe('practice refresh after a successful load', () => {
  it('retains the last successful data after a background request fails', async () => {
    vi.mocked(fetchAuthProfile).mockResolvedValueOnce(record).mockRejectedValueOnce(new Error('Unavailable'))
    await render().refresh()
    await render().refresh(true)
    expect(render()).toMatchObject({ data: record, loading: false, error: 'Unavailable' })
  })

  it('keeps the refresh warning until a later request actually succeeds', async () => {
    vi.mocked(fetchAuthProfile).mockResolvedValueOnce(record).mockRejectedValueOnce(new Error('Unavailable'))
    await render().refresh()
    await render().refresh(true)
    const next = pending<typeof record>()
    vi.mocked(fetchAuthProfile).mockReturnValueOnce(next.promise)
    const request = render().refresh(true)
    expect(render()).toMatchObject({ data: record, loading: false, error: 'Unavailable' })
    next.resolve(record)
    await request
    expect(render()).toMatchObject({ data: record, loading: false, error: null })
  })

  it('ignores an outdated failed refresh after a newer response succeeds', async () => {
    vi.mocked(fetchAuthProfile).mockResolvedValueOnce(record)
    await render().refresh()
    const old = pending<typeof record>()
    const newer = { ...record, overall_elo: 900 }
    vi.mocked(fetchAuthProfile).mockReturnValueOnce(old.promise).mockResolvedValueOnce(newer)
    const oldRequest = render().refresh(true)
    await render().refresh(true)
    old.reject(new Error('Outdated failure'))
    await oldRequest
    expect(render()).toMatchObject({ data: newer, error: null, loading: false })
  })

  it('reports an initial failure when no successful data exists', async () => {
    vi.mocked(fetchAuthProfile).mockRejectedValueOnce(new Error('Unavailable'))
    await render().refresh()
    expect(render()).toMatchObject({ data: null, error: 'Unavailable', loading: false })
  })
})
