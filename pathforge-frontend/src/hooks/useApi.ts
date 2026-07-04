'use client'

import { useCallback, useEffect, useState } from 'react'
import { analyzeCode, fetchGaps, fetchElo, fetchRecommendations } from '@/services/api/endpoints'
import { fetchAuthProfile } from '@/services/api/auth'
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  GapResponse,
  EloResponse,
  RecommendResponse,
  AuthProfile,
} from '@/types/api'

function useApiData<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
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
  }, deps)

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
  )
}

export function useGapData(userId: number) {
  return useApiData<GapResponse>(
    () => fetchGaps({ user_id: userId }),
    [userId],
  )
}

export function useRecommendations(userId: number) {
  return useApiData<RecommendResponse>(
    () => fetchRecommendations({ user_id: userId }),
    [userId],
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
