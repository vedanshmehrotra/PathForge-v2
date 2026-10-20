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
  return practiceKindLabel(response, item) ? item.reason : null
}

export function isPracticePolicy(response: RecommendResponse | null) {
  return response?.policy === 'recorded_practice_v1' || response?.policy === 'calendar_practice_v2'
}

export function practiceKindLabel(response: RecommendResponse | null, item: RecommendResponse['recommendations'][number]) {
  if (!isPracticePolicy(response)) return null
  if (item.practice_kind === 'revisit') return 'Revisit a problem'
  if (item.practice_kind === 'explore') return 'Try something different'
  if (response?.policy !== 'calendar_practice_v2') return null
  if (item.practice_kind === 'related_return') return 'Return to a topic'
  if (item.practice_kind === 'follow_up') return 'Continue a topic'
  if (item.practice_kind === 'starter') return 'A place to start'
  return null
}

export function practiceEmptyMessage(state: RecommendResponse['state']) {
  if (state === 'session_exhausted') return 'You have skipped the available choices for this session. Reset skips or try another difficulty.'
  if (state === 'caught_up') return 'No more eligible choices right now. Try another difficulty or bring a problem of your own.'
  return 'No practice suggestions are available from the current problem bank for this difficulty.'
}
