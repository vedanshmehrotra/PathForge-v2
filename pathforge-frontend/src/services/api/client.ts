const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pathforge-v2.onrender.com'

let _accessToken: string | null = null

export function setAccessToken(token: string | null) {
  _accessToken = token
}

export class ApiError extends Error {
  public code?: string
  public reason?: string

  constructor(
    public status: number,
    message: string,
    public body?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
    const detail = (body as { detail?: unknown } | null)?.detail
    if (detail && typeof detail === 'object') {
      const fields = detail as { code?: unknown; reason?: unknown }
      if (typeof fields.code === 'string') this.code = fields.code
      if (typeof fields.reason === 'string') this.reason = fields.reason
    }
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit & { timeoutMs?: number } = {},
): Promise<T> {
  const { timeoutMs, ...requestOptions } = options
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (_accessToken) {
    headers['Authorization'] = `Bearer ${_accessToken}`
  }

  const controller = new AbortController()
  const abort = () => controller.abort()
  requestOptions.signal?.addEventListener('abort', abort, { once: true })
  if (requestOptions.signal?.aborted) controller.abort()
  let timedOut = false
  const timer = timeoutMs ? setTimeout(() => { timedOut = true; controller.abort() }, timeoutMs) : undefined
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...requestOptions, headers, signal: controller.signal,
    })

    if (!res.ok) {
      const body = await res.json().catch(() => null)
      const message = typeof body?.detail === 'string'
        ? body.detail
        : typeof body?.detail?.message === 'string'
          ? body.detail.message
          : typeof body?.detail?.error === 'string'
            ? body.detail.error
            : typeof body?.error === 'string'
              ? body.error
              : `Request failed with status ${res.status}`
      throw new ApiError(res.status, message, body)
    }

    return await res.json()
  } catch (error) {
    if (timedOut) throw new ApiError(408, 'The request took too long. Please retry.')
    throw error
  } finally {
    if (timer) clearTimeout(timer)
    requestOptions.signal?.removeEventListener('abort', abort)
  }
}
