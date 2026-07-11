const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pathforge-v2.onrender.com'

let _accessToken: string | null = null

export function setAccessToken(token: string | null) {
  _accessToken = token
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
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
    throw new ApiError(
      res.status,
      body?.detail || body?.error || `Request failed with status ${res.status}`,
      body,
    )
  }

  return res.json()
}
