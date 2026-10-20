'use client'

import { useCallback, useMemo, useSyncExternalStore } from 'react'

const SKIP_DAYS = 30
const EVENT = 'pathforge-practice-skips'
const memory = new Map<string, string>()

function subscribe(callback: () => void) {
  window.addEventListener('storage', callback)
  window.addEventListener(EVENT, callback)
  return () => {
    window.removeEventListener('storage', callback)
    window.removeEventListener(EVENT, callback)
  }
}

export function readSkips(raw: string | null, now = Date.now()): Array<{ id: string; until: number }> {
  try {
    const value = JSON.parse(raw ?? '[]')
    if (!Array.isArray(value)) return []
    const seen = new Set<string>()
    return value.filter((entry): entry is { id: string; until: number } => {
      if (!entry || typeof entry.id !== 'string' || !entry.id.trim() || entry.id.length > 100 ||
        typeof entry.until !== 'number' || !Number.isFinite(entry.until) || entry.until <= now ||
        entry.until > now + SKIP_DAYS * 86400000 || seen.has(entry.id)) return false
      seen.add(entry.id)
      return true
    }).slice(0, 50)
  } catch {
    return []
  }
}

export function usePracticeSkips(userId: number) {
  const key = `pathforge.practice-skips.v1.${userId}`
  const snapshot = useCallback(() => {
    try { return memory.get(key) ?? window.localStorage.getItem(key) ?? '' } catch { return memory.get(key) ?? '' }
  }, [key])
  const raw = useSyncExternalStore(subscribe, snapshot, () => null)
  const entries = useMemo(() => readSkips(raw), [raw])
  const update = useCallback((id?: string) => {
    if (userId <= 0) return
    const previous = readSkips(snapshot())
    if (id && previous.length >= 50 && !previous.some(entry => entry.id === id)) return
    const next = id ? [...previous.filter(entry => entry.id !== id),
      { id, until: Date.now() + SKIP_DAYS * 86400000 }].slice(-50) : []
    try {
      window.localStorage.setItem(key, JSON.stringify(next))
      memory.delete(key)
      window.dispatchEvent(new Event(EVENT))
    } catch {
      // Still allow skips for this tab if browser persistence is unavailable.
      memory.set(key, JSON.stringify(next))
      window.dispatchEvent(new Event(EVENT))
    }
  }, [key, snapshot, userId])
  return { ready: raw !== null, excludedIds: entries.map(entry => entry.id),
    persistent: !memory.has(key),
    skip: (id: string) => update(id), reset: () => update() }
}
