'use client'

import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { useAuthProfile, useRecommendations } from '@/hooks/useApi'
import { useAuth } from '@/auth/AuthProvider'
import { relativeTime } from '@/lib/utils'
import { RecommendationLink } from '@/components/recommendation-link'
import { practiceReason, uniqueRecommendations } from '@/services/recommendations'

export function DifficultyBadge({ difficulty }: { difficulty: 'Easy' | 'Medium' | 'Hard' }) {
  const variant = difficulty === 'Easy' ? 'success' : difficulty === 'Medium' ? 'warning' : 'danger'
  return <Badge variant={variant}>{difficulty}</Badge>
}

export function DashboardView() {
  const { data, loading, error, refresh } = useAuthProfile()
  const activity = [...(data?.profiles ?? [])]
    .filter(p => p.last_attempt_at || p.attempt_count > 0)
    .sort((a, b) => (b.last_attempt_at ?? '').localeCompare(a.last_attempt_at ?? ''))
    .slice(0, 5)
  const hasHistory = activity.length > 0 && !error

  return (
    <div className="workspace-page">
      <header className="page-intro">
        <p className="workspace-kicker">Your practice workspace</p>
        <h1 className="page-heading">Dashboard</h1>
        <p className="page-description">A place to understand an approach and choose what to explore next.</p>
      </header>

      <section className="grid gap-8 border-y border-border py-8 lg:grid-cols-[1.5fr_1fr] lg:gap-12" aria-labelledby="start-heading">
        <div>
          <h2 id="start-heading" className="text-2xl font-medium tracking-tight sm:text-3xl">
            {hasHistory ? 'Take another look at how you solve.' : 'Start with a solution you know.'}
          </h2>
          <p className="mt-4 max-w-xl text-base leading-relaxed text-muted-foreground">
            Paste a Python solution to inspect its patterns. Add a problem when you want to compare
            the evidence with available approaches.
          </p>
          <Link href="/analysis" className="action-primary mt-6">Analyze a solution <ArrowRight className="size-4" /></Link>
        </div>
        <div className="lg:border-l lg:border-border lg:pl-8">
          <h3 className="section-title">What you will get</h3>
          <ul className="mt-4 space-y-3 text-sm leading-relaxed text-muted-foreground">
            <li>Patterns supported by evidence in your code.</li>
            <li>A comparison with available solution approaches.</li>
            <li>A clear explanation when the evidence is inconclusive.</li>
          </ul>
          <p className="mt-4 text-sm text-muted-foreground">Pattern analysis does not run your code or verify correctness.</p>
        </div>
      </section>

      <div className="grid gap-10 xl:grid-cols-[1.3fr_1fr] xl:gap-12">
        <RecommendedPreview />
        <section aria-labelledby="recent-heading">
          <div className="flex items-center justify-between gap-4">
            <h2 id="recent-heading" className="section-title">Recently practised patterns</h2>
            <Link href="/progress" className="text-link">View history</Link>
          </div>
          {loading ? <p role="status" className="mt-5 text-sm text-muted-foreground">Loading your practice history...</p> : error ? (
            <div className="mt-5">
              <p role="alert" className="text-sm">Could not load practice history. {error}</p>
              <button type="button" onClick={refresh} className="text-link mt-3">Retry history</button>
            </div>
          ) : activity.length === 0 ? (
            <p className="mt-5 text-sm leading-relaxed text-muted-foreground">
              Your recorded patterns will appear here after analysis. You can begin without a rating or a practice history.
            </p>
          ) : (
            <ul className="mt-4 divide-y divide-border">
              {activity.map(p => (
                <li key={p.topic} className="flex flex-wrap items-baseline justify-between gap-2 py-4">
                  <span className="text-sm capitalize">{p.topic.replace(/_/g, ' ')}</span>
                  <span className="text-xs text-muted-foreground">{p.last_attempt_at ? relativeTime(p.last_attempt_at) : 'Recorded previously'}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}

export function RecommendedPreview() {
  const { profile } = useAuth()
  const { data, loading, error, refresh } = useRecommendations(profile?.user_id ?? 0)
  const items = uniqueRecommendations(data?.recommendations ?? []).slice(0, 2)

  return (
    <section aria-labelledby="practice-heading">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="practice-heading" className="section-title">Find your next problem</h2>
        <Link href="/recommendations" className="text-link">Browse practice <ArrowRight className="size-3.5" /></Link>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">Choices from the current problem bank, informed by recorded practice when available. These are not a diagnosis of your skills.</p>
      {loading ? <p role="status" className="mt-5 text-sm text-muted-foreground">Loading practice suggestions...</p> : error ? (
        <div className="mt-5">
          <p role="alert" className="text-sm">Could not load practice suggestions. {error}</p>
          <button type="button" onClick={refresh} className="text-link mt-3">Retry</button>
        </div>
      ) : items.length === 0 ? (
        <p className="mt-5 text-sm text-muted-foreground">No practice suggestions are available from the current problem bank.</p>
      ) : (
        <div className="mt-4 divide-y divide-border">
          {items.map(r => (
            <div key={r.problem_id} className="flex flex-col gap-4 py-5 sm:flex-row sm:items-center">
              <div className="min-w-0 flex-1">
                <p className="text-base font-medium">{r.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{r.difficulty || 'Difficulty not listed'}</p>
                {practiceReason(data, r) && <p className="mt-2 text-sm text-muted-foreground">{practiceReason(data, r)}</p>}
              </div>
              <RecommendationLink url={r.problem_url} title={r.title} />
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
