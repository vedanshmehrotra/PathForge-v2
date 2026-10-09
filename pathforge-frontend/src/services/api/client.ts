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
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (_accessToken) {
    headers['Authorization'] = `Bearer ${_accessToken}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const message = typeof body?.detail === 'string'
      ? body.detail
      : typeof body?.detail?.message === 'string'
        ? body.detail.message
        : typeof body?.error === 'string'
          ? body.error
          : `Request failed with status ${res.status}`
    throw new ApiError(
      res.status,
      message,
      body,
    )
  }

  return res.json()
}
