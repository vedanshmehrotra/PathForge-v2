'use client'

import { useCallback, useEffect, useState } from 'react'
import { analyzeCode, prepareProblem, fetchGaps, fetchElo, fetchRecommendations } from '@/services/api/endpoints'
import { fetchAuthProfile } from '@/services/api/auth'
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

export function useAuthProfile() {
  return useApiData<AuthProfile>(fetchAuthProfile)
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

export function useAnalyzeCode() {
  const [result, setResult] = useState<AnalyzeResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = useCallback(async (req: AnalyzeRequest) => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await analyzeCode(req)
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }, [])

  return { result, loading, error, run }
}

export function usePrepareProblem() {
  const [result, setResult] = useState<PrepareResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = useCallback(async (problem: string) => {
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
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Preparation failed')
    } finally {
      setLoading(false)
    }
  }, [])

  const clear = useCallback(() => setResult(null), [])

  return { result, loading, error, run, clear }
}
