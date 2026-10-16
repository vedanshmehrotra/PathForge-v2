import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiRequest } from '../api/client'

afterEach(() => vi.unstubAllGlobals())

describe('API error contract', () => {
  it('retains preparation codes and displays structured messages', async () => {
    const detail = { code: 'PREPARATION_REQUIRED', reason: 'GROUND_TRUTH_MISSING', message: 'Prepare this problem first.' }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 409, json: async () => ({ detail }) }))
    await expect(apiRequest('/analyze')).rejects.toMatchObject({
      status: 409, code: detail.code, reason: detail.reason, message: detail.message,
      body: { detail },
    })
  })

  it('preserves readable string errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 502, json: async () => ({ detail: 'Preparation failed' }) }))
    await expect(apiRequest('/prepare-problem')).rejects.toMatchObject({ status: 502, message: 'Preparation failed' })
  })

  it('uses a readable fallback for malformed errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({ detail: {} }) }))
    await expect(apiRequest('/analyze')).rejects.toThrow('Request failed with status 500')
  })

  it('does not invent a recovery code for unstructured errors', () => {
    expect(new ApiError(404, 'Not found', { detail: 'Not found' }).code).toBeUndefined()
  })
})
