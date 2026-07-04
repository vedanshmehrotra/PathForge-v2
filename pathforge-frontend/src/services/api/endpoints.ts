import { apiRequest } from './client'
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  GapRequest,
  GapResponse,
  EloRequest,
  EloResponse,
  RecommendRequest,
  RecommendResponse,
} from '@/types/api'

export function analyzeCode(req: AnalyzeRequest): Promise<AnalyzeResponse> {
  return apiRequest<AnalyzeResponse>('/analyze', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function fetchGaps(req: GapRequest): Promise<GapResponse> {
  return apiRequest<GapResponse>('/gaps', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function fetchElo(req: EloRequest): Promise<EloResponse> {
  return apiRequest<EloResponse>('/elo', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function fetchRecommendations(
  req: RecommendRequest,
): Promise<RecommendResponse> {
  return apiRequest<RecommendResponse>('/recommend', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}
