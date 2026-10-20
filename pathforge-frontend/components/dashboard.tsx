'use client'

import Link from 'next/link'
import { ArrowRight, Braces, Compass, Layers2, Route } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { useAuthProfile, useRecommendations } from '@/hooks/useApi'
import { useAuth } from '@/auth/AuthProvider'
import { usePracticeSkips } from '@/hooks/usePracticeSkips'
import { relativeTime } from '@/lib/utils'
import { RecommendationLink } from '@/components/recommendation-link'
import { practiceKindLabel, practiceReason, uniqueRecommendations } from '@/services/recommendations'

export function DifficultyBadge({ difficulty }: { difficulty: 'Easy' | 'Medium' | 'Hard' }) {
  const variant = difficulty === 'Easy' ? 'success' : difficulty === 'Medium' ? 'warning' : 'danger'
  return <Badge variant={variant}>{difficulty}</Badge>
}

export function DashboardView() {
  const { data, loading, error, refresh } = useAuthProfile()
  const activity = [...(data?.practice_records ?? data?.profiles ?? [])]
    .filter(p => p.last_attempt_at || p.attempt_count > 0)
    .sort((a, b) => (b.last_attempt_at ?? '').localeCompare(a.last_attempt_at ?? ''))
    .slice(0, 5)
  const hasHistory = activity.length > 0 && !error

  return (
    <div className="workspace-page">
      <header className="page-intro">
        <p className="workspace-kicker flex items-center gap-2"><Route className="size-4 text-mint" />Your practice workspace</p>
        <h1 className="page-heading">Dashboard</h1>
        <p className="page-description">A place to understand an approach and choose what to explore next.</p>
      </header>

      <section className="grid gap-7 border-y border-border py-7 lg:grid-cols-[1.2fr_1fr] lg:items-center lg:gap-10" aria-labelledby="start-heading">
        <div>
          <h2 id="start-heading" className="text-2xl font-medium tracking-tight sm:text-3xl">
            {hasHistory ? 'Take another look at how you solve.' : 'Start with a solution you know.'}
          </h2>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground">
            Paste a Python solution to inspect its patterns. Add a problem when you want to compare
            the evidence with available approaches.
          </p>
          <Link href="/analysis" className="action-primary mt-5">Analyze a solution <ArrowRight className="size-4" /></Link>
        </div>
        <div className="min-w-0 lg:border-l lg:border-border lg:pl-8">
          <div className="mb-4 flex items-center gap-2 text-xs text-muted-foreground"><Braces className="size-4 text-mint" />A closer look at your solution<span className="ml-auto font-mono text-[10px]">.py</span></div>
          <div className="space-y-2 border-l border-mint/30 pl-4 font-mono text-xs leading-relaxed" aria-hidden="true"><p className="text-muted-foreground">for index in range(width, len(values)):</p><p className="text-mint">&nbsp; window += values[index]</p><p className="text-amber">&nbsp; window -= values[index - width]</p></div>
          <div className="mt-5 grid grid-cols-3 gap-2 border-t border-border pt-4 text-[11px] text-muted-foreground"><span className="flex items-center gap-1.5"><Braces className="size-3.5 text-mint" />Inspect</span><span className="flex items-center gap-1.5"><Layers2 className="size-3.5 text-sky" />Compare</span><span className="flex items-center gap-1.5"><Compass className="size-3.5 text-amber" />Practise</span></div>
          <p className="mt-3 text-[11px] text-muted-foreground">Illustrative structure. Pattern analysis does not run your code or verify correctness.</p>
        </div>
      </section>

      <div className="grid gap-8 xl:grid-cols-[1.2fr_1fr] xl:gap-10">
        <RecommendedPreview />
        <section className="min-w-0" aria-labelledby="recent-heading">
          <div className="flex items-center justify-between gap-4">
            <h2 id="recent-heading" className="section-title flex items-center gap-2"><Route className="size-4 text-mint" />Recently practised patterns</h2>
            <Link href="/progress" className="text-link">View history</Link>
          </div>
          {loading ? <p role="status" className="mt-5 text-sm text-muted-foreground">Loading your practice history...</p> : error ? (
            <div className="mt-5">
              <p role="alert" className="text-sm">Could not load practice history. {error}</p>
              <button type="button" onClick={() => refresh()} className="text-link mt-3">Retry history</button>
            </div>
          ) : activity.length === 0 ? (
            <p className="mt-5 text-sm leading-relaxed text-muted-foreground">
              Your recorded patterns will appear here after analysis. You can begin without a rating or a practice history.
            </p>
          ) : (
            <ul className="mt-4">
              {activity.map(p => (
                <li key={p.topic} className="relative ml-1 flex flex-wrap items-baseline justify-between gap-2 border-l border-border py-3 pl-5 last:border-transparent">
                  <span className="absolute -left-[4px] top-[19px] size-[7px] rounded-full bg-mint ring-4 ring-background" aria-hidden="true" /><span className="text-sm capitalize">{p.topic.replace(/_/g, ' ')}</span>
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
  const { profile, loading: authLoading, profileLoading, profileError, retryProfile } = useAuth()
  const skips = usePracticeSkips(profile?.user_id ?? 0)
  const { data, loading, error, refresh } = useRecommendations(skips.ready ? profile?.user_id ?? 0 : 0, undefined, skips.excludedIds)
  const items = uniqueRecommendations(data?.recommendations ?? [])

  return (
    <section className="min-w-0" aria-labelledby="practice-heading">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="practice-heading" className="section-title flex items-center gap-2"><Compass className="size-4 text-amber" />Find your next problem</h2>
        <Link href="/recommendations" className="text-link">Browse practice <ArrowRight className="size-3.5" /></Link>
      </div>
      <p className="mt-3 text-xs leading-relaxed text-muted-foreground">A mix from your recorded practice and the current bank, without a skill diagnosis.</p>
      {authLoading || profileLoading || !skips.ready ? <p role="status" className="mt-5 text-sm text-muted-foreground">Loading your account...</p> : !profile ? (
        <div className="mt-5"><p role="alert">{profileError ?? 'Your account is unavailable.'}</p>
          <button type="button" onClick={retryProfile} className="text-link mt-3">Retry account</button></div>
      ) : loading ? <p role="status" className="mt-5 text-sm text-muted-foreground">Loading practice suggestions...</p> : error ? (
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
                {practiceKindLabel(data, r) && <p className="mb-2 text-xs font-medium text-mint">{practiceKindLabel(data, r)}</p>}
                <p className="text-sm font-semibold">{r.title}</p>
                <div className="mt-2">{r.difficulty ? <DifficultyBadge difficulty={r.difficulty as 'Easy' | 'Medium' | 'Hard'} /> : <span className="text-xs text-muted-foreground">Difficulty not listed</span>}</div>
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
