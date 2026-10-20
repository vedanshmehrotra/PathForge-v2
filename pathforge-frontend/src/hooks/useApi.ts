'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { analyzeCode, prepareProblem, fetchGaps, fetchElo, fetchRecommendations } from '@/services/api/endpoints'
import { fetchAuthProfile } from '@/services/api/auth'
import { ApiError } from '@/services/api/client'
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  PrepareResponse,
  GapResponse,
  EloResponse,
  RecommendResponse,
  AuthProfile,
  UnscoredApproach,
} from '@/types/api'

function useApiData<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
  skip = false,
  live = false,
) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(!skip)
  const [error, setError] = useState<string | null>(null)
  const requestId = useRef(0)

  const refresh = useCallback(async (background = false) => {
    if (skip) return
    const id = ++requestId.current
    if (!background) setLoading(true)
    setError(null)
    try {
      const result = await fetcher()
      if (id === requestId.current) setData(result)
    } catch (e) {
      if (id === requestId.current) setError(e instanceof Error ? e.message : 'Request failed')
    } finally {
      if (id === requestId.current) setLoading(false)
    }
  }, [...deps, skip])

  useEffect(() => {
    refresh()
    return () => { ++requestId.current }
  }, [refresh])

  useEffect(() => {
    if (!live || skip) return
    const reload = () => { if (document.visibilityState === 'visible') void refresh(true) }
    window.addEventListener('focus', reload)
    document.addEventListener('visibilitychange', reload)
    const timer = window.setInterval(reload, 30000)
    return () => {
      window.removeEventListener('focus', reload)
      document.removeEventListener('visibilitychange', reload)
      window.clearInterval(timer)
    }
  }, [live, skip, refresh])

  return { data, loading, error, refresh }
}

export function useEloData(userId: number) {
  return useApiData<EloResponse>(
    () => fetchElo({ user_id: userId }),
    [userId],
    !userId || userId <= 0,
    true,
  )
}

export function useGapData(userId: number) {
  return useApiData<GapResponse>(
    () => fetchGaps({ user_id: userId }),
    [userId],
    !userId || userId <= 0,
  )
}

export function useRecommendations(userId: number, difficulty?: 'Easy' | 'Medium' | 'Hard', excludedIds: string[] = []) {
  const [revision, setRevision] = useState(0)
  const exclusions = JSON.stringify(excludedIds)
  const key = JSON.stringify([userId, difficulty, exclusions, revision])
  const [state, setState] = useState<{
    key: string; data: RecommendResponse | null; error: string | null
  } | null>(null)
  const refresh = useCallback(() => setRevision(value => value + 1), [])

  useEffect(() => {
    if (userId <= 0) return
    let active = true
    fetchRecommendations({ user_id: userId, mode: 'practice', policy: 'calendar_practice_v2',
      difficulty, excluded_ids: JSON.parse(exclusions) })
      .then(data => { if (active) setState({ key, data, error: null }) })
      .catch(e => { if (active) setState({ key, data: null, error: e instanceof Error ? e.message : 'Request failed' }) })
    return () => { active = false }
  }, [userId, difficulty, exclusions, key])

  // Never render another account/filter's data while its request is in flight.
  const current = state?.key === key ? state : null
  return { data: userId > 0 ? current?.data ?? null : null,
    error: userId > 0 ? current?.error ?? null : null,
    loading: userId > 0 && current === null, refresh }
}

// Topic profiles (attempts, pass counts, accuracy, last attempt) from the
// existing GET /auth/profile endpoint. Used to show real practice history.
export function useAuthProfile() {
  return useApiData<AuthProfile>(() => fetchAuthProfile(), [], false, true)
}

export function useAnalyzeCode() {
  const [result, setResult] = useState<AnalyzeResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [errorCode, setErrorCode] = useState<string | null>(null)

  const run = useCallback(async (req: AnalyzeRequest) => {
    setLoading(true)
    setError(null)
    setErrorCode(null)
    setResult(null)
    try {
      const res = await analyzeCode(req)
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed')
      setErrorCode(e instanceof ApiError ? e.code ?? null : null)
    } finally {
      setLoading(false)
    }
  }, [])

  return { result, loading, error, errorCode, run }
}

export function usePrepareProblem() {
  const [result, setResult] = useState<PrepareResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [unsupported, setUnsupported] = useState<UnscoredApproach[] | null>(null)
  const requestId = useRef(0)

  const run = useCallback(async (problem: string) => {
    const id = ++requestId.current
    setLoading(true)
    setError(null)
    setResult(null)
    setUnsupported(null)
    const slug = problem.includes('/') ? problem.split('/').filter(Boolean).pop() : problem
    try {
      const res = await prepareProblem({
        problem: slug && /^\d+$/.test(slug)
          ? { leetcode_id: parseInt(slug, 10) }
          : { title_slug: slug },
      })
      if (id === requestId.current) setResult(res)
    } catch (e) {
      if (id === requestId.current) {
        setError(e instanceof Error ? e.message : 'Preparation failed')
        if (e instanceof ApiError && e.status === 409 && e.code === 'COMPARISON_UNSUPPORTED') {
          const detail = (e.body as { detail?: { approaches?: unknown } } | null)?.detail
          const proposals = detail?.approaches
          // A malformed/older diagnostic still cannot unlock prepared analysis.
          setUnsupported(Array.isArray(proposals) ? proposals.filter((item): item is UnscoredApproach =>
            item && item.comparison_support === 'UNSUPPORTED' && item.contract_version === 2 &&
            typeof item.id === 'string' && typeof item.name === 'string' &&
            typeof item.description === 'string' && typeof item.coverage_limit === 'string' &&
            Array.isArray(item.patterns) && item.patterns.length === 0) : [])
        }
      }
    } finally {
      if (id === requestId.current) setLoading(false)
    }
  }, [])

  const clear = useCallback(() => {
    ++requestId.current
    setResult(null)
    setError(null)
    setUnsupported(null)
    setLoading(false)
  }, [])

  return { result, loading, error, unsupported, run, clear }
}
