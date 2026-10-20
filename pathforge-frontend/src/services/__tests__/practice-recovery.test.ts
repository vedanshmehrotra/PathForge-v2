import { afterEach, describe, expect, it, vi } from 'vitest'
import { readSkips } from '../../hooks/usePracticeSkips'
import { apiRequest } from '../api/client'

afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals() })

describe('persistent browser skips', () => {
  it('retains active unique skips and expires old or malformed entries', () => {
    const now = Date.now()
    expect(readSkips(JSON.stringify([
      {id: '7', until: now + 86400000}, {id: '7', until: now + 5000},
      {id: '8', until: now - 1}, {id: '9', until: now + 31 * 86400000}, null,
      {id: '', until: now + 100}, {id: 10, until: now + 100},
    ]), now)).toEqual([{id: '7', until: now + 86400000}])
    expect(readSkips('broken', now)).toEqual([])
  })

  it('caps untrusted persisted data to the API exclusion limit', () => {
    const now = Date.now()
    expect(readSkips(JSON.stringify(Array.from({length: 100}, (_, i) => ({id: `${i}`, until: now + 1000}))), now)).toHaveLength(50)
  })
})

it('a hung account or recommendation request fails with a retryable message', async () => {
  vi.useFakeTimers()
  vi.stubGlobal('fetch', vi.fn((_url, options: RequestInit) => new Promise((_resolve, reject) => {
    options.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
  })))
  const request = apiRequest('/recommend', {timeoutMs: 20000})
  const assertion = expect(request).rejects.toMatchObject({status: 408, message: 'The request took too long. Please retry.'})
  await vi.advanceTimersByTimeAsync(20000)
  await assertion
  expect(fetch).toHaveBeenCalledTimes(1)
})
