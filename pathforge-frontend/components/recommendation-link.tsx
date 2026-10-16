import { ArrowUpRight } from 'lucide-react'
import { problemUrl } from '@/services/recommendations'

export function RecommendationLink({ url, title }: { url?: string | null; title: string }) {
  const destination = problemUrl(url)
  if (!destination) return <span className="text-xs text-muted-foreground">Problem link unavailable</span>
  return (
    <a href={destination} target="_blank" rel="noopener noreferrer"
      aria-label={`Open ${title} on LeetCode`}
      className="action-secondary shrink-0">
      Open on LeetCode <ArrowUpRight className="size-4" aria-hidden="true" />
    </a>
  )
}
