import type { RecommendResponse } from '@/types/api'

export function problemUrl(value: unknown): string | null {
  if (typeof value !== 'string' || /[\x00-\x20\\]/.test(value)) return null
  try {
    const url = new URL(value)
    if (url.protocol !== 'https:' || !['leetcode.com', 'www.leetcode.com'].includes(url.hostname)
      || url.username || url.password || url.port || url.search || url.hash
      || !/^\/problems\/[a-z0-9]+(?:-[a-z0-9]+)*\/?$/.test(url.pathname)) return null
    return `https://leetcode.com${url.pathname.replace(/\/$/, '')}/`
  } catch {
    return null
  }
}

export function uniqueRecommendations(items: RecommendResponse['recommendations']) {
  const seen = new Set<string>()
  return items.filter(item => {
    if (seen.has(item.problem_id)) return false
    seen.add(item.problem_id)
    return true
  })
}

export function practiceReason(response: RecommendResponse | null, item: RecommendResponse['recommendations'][number]) {
  return response?.policy === 'recorded_practice_v1'
    && (item.practice_kind === 'explore' || item.practice_kind === 'revisit') ? item.reason : null
}

export function practiceEmptyMessage(state: RecommendResponse['state']) {
  if (state === 'session_exhausted') return 'You have skipped the available choices for this session. Reset skips or try another difficulty.'
  if (state === 'caught_up') return 'Only your latest recorded problem is available here. Try another difficulty or bring a problem of your own.'
  return 'No practice suggestions are available from the current problem bank for this difficulty.'
}
