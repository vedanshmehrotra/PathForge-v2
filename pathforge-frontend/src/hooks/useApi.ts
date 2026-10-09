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
} from '@/types/api'

function useApiData<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
  skip = false,
) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(!skip)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (skip) return
    setLoading(true)
    setError(null)
    try {
      const result = await fetcher()
      setData(result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }, [...deps, skip])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { data, loading, error, refresh }
}

export function useEloData(userId: number) {
  return useApiData<EloResponse>(
    () => fetchElo({ user_id: userId }),
    [userId],
    !userId || userId <= 0,
  )
}

export function useGapData(userId: number) {
  return useApiData<GapResponse>(
    () => fetchGaps({ user_id: userId }),
    [userId],
    !userId || userId <= 0,
  )
}

export function useRecommendations(userId: number) {
  return useApiData<RecommendResponse>(
    () => fetchRecommendations({ user_id: userId }),
    [userId],
    !userId || userId <= 0,
  )
}

// Topic profiles (attempts, pass counts, accuracy, last attempt) from the
// existing GET /auth/profile endpoint. Used to show real practice history.
export function useAuthProfile() {
  return useApiData<AuthProfile>(() => fetchAuthProfile(), [], false)
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
  const requestId = useRef(0)

  const run = useCallback(async (problem: string) => {
    const id = ++requestId.current
    setLoading(true)
    setError(null)
    setResult(null)
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
      }
    } finally {
      if (id === requestId.current) setLoading(false)
    }
  }, [])

  const clear = useCallback(() => {
    ++requestId.current
    setResult(null)
    setError(null)
    setLoading(false)
  }, [])

  return { result, loading, error, run, clear }
}
