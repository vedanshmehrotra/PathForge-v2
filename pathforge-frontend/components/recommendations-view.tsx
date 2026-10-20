'use client'

import { useState } from 'react'
import { Panel, PanelBody } from '@/components/ui/panel'
import { DifficultyBadge } from '@/components/dashboard'
import { RecommendationLink } from '@/components/recommendation-link'
import { cn } from '@/lib/utils'
import { useRecommendations } from '@/hooks/useApi'
import { useAuth } from '@/auth/AuthProvider'
import { usePracticeSkips } from '@/hooks/usePracticeSkips'
import { isPracticePolicy, practiceEmptyMessage, practiceKindLabel, practiceReason, uniqueRecommendations } from '@/services/recommendations'

const FILTERS = ['All', 'Easy', 'Medium', 'Hard'] as const

export function RecommendationsView() {
  const { profile, loading, profileLoading, profileError, retryProfile } = useAuth()
  if (loading || profileLoading) return <p role="status">Loading your account...</p>
  if (!profile) return <div role="alert"><p>{profileError ?? 'Your account is unavailable.'}</p>
    <button type="button" onClick={retryProfile} className="action-primary mt-3">Retry account</button></div>
  return <PracticeSuggestions key={profile?.user_id ?? 0} userId={profile?.user_id ?? 0} />
}

function PracticeSuggestions({ userId }: { userId: number }) {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>('All')
  const { ready, excludedIds, skip, reset, persistent } = usePracticeSkips(userId)
  const { data: recData, loading, error, refresh } = useRecommendations(
    ready ? userId : 0, filter === 'All' ? undefined : filter, excludedIds,
  )
  const items = uniqueRecommendations(recData?.recommendations ?? [])
  const list = items.filter(r => filter === 'All' || r.difficulty === filter)

  return (
    <div className="workspace-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="workspace-kicker">Choose your next session</p>
          <h1 className="page-heading">Recommendations</h1>
          <p className="page-description">Find a problem you want to think about.</p>
          <p className="mt-3 max-w-xl text-sm text-muted-foreground">{isPracticePolicy(recData)
            ? 'Related topics, an older problem, or something different. Based on practice saved with a problem selected.'
            : 'Choices from the current problem bank. These do not establish correctness or mastery.'}</p>
          {recData?.history?.truncated && <p className="mt-2 text-sm text-muted-foreground">Using your latest recorded problems; older practice may not be represented.</p>}
          {!!recData?.history?.code_only_submissions && <p className="mt-2 text-sm text-muted-foreground">Code-only inspections are saved, but do not identify a problem for recommendations.</p>}
          {filter === 'All' && recData?.context?.default_max_difficulty && <p className="mt-2 text-sm text-muted-foreground">Showing up to {recData.context.default_max_difficulty}. Choose another difficulty whenever you want.</p>}
          {!!recData?.history?.unmapped_submissions && <p className="mt-2 text-sm text-muted-foreground">Some recorded problems could not be linked to the current bank.</p>}
          {!!recData?.history?.invalid_timestamps && <p className="mt-2 text-sm text-muted-foreground">Some practice dates are unavailable; return suggestions may be limited.</p>}
        </div>
        <div className="flex gap-1 rounded-md border border-border bg-card p-0.5" aria-label="Filter difficulty">
          {FILTERS.map(f => (
            <button key={f} type="button" onClick={() => setFilter(f)} aria-pressed={filter === f}
              className={cn('min-h-11 rounded px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-primary',
                filter === f ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:text-foreground')}>
              {f}
            </button>
          ))}
        </div>
      </div>

      {excludedIds.length > 0 && <div className="flex flex-wrap items-center gap-3 text-sm">
        <span className="text-muted-foreground">{persistent ? 'Skips are saved in this browser for 30 days.' : 'Browser storage is unavailable. Skips last in this tab.'}</span>
        <button type="button" onClick={reset} className="text-link">Reset skips</button>
        {excludedIds.length >= 50 && <span className="text-muted-foreground">50 active skips. Reset skips to choose from those problems again.</span>}
      </div>}

      {!ready || loading ? <p role="status" className="text-sm text-muted-foreground">Loading practice suggestions...</p> : error ? (
        <Panel><PanelBody>
          <p role="alert" className="text-sm">Could not load practice suggestions. {error}</p>
          <button type="button" onClick={refresh} className="action-primary mt-3">Retry</button>
        </PanelBody></Panel>
      ) : items.length === 0 ? (
        <Panel><PanelBody>
          <p role="status" className="text-sm text-muted-foreground">{practiceEmptyMessage(recData?.state)}</p>
          <button type="button" onClick={refresh} className="text-link mt-3">Refresh suggestions</button>
        </PanelBody></Panel>
      ) : list.length === 0 ? (
        <Panel><PanelBody>
          <p className="text-sm text-muted-foreground">No {filter} suggestions are in this list. Choose another difficulty.</p>
          <button type="button" onClick={() => setFilter('All')} className="text-link mt-3">Clear difficulty filter</button>
        </PanelBody></Panel>
      ) : (
        <div className="divide-y divide-border border-y border-border">
          {list.map(r => (
            <article key={r.problem_id}>
              <div className="flex flex-col gap-4 py-6 md:flex-row md:items-center">
                <div className="min-w-0 flex-1">
                  {practiceKindLabel(recData, r) && <p className="mb-2 text-xs font-medium text-mint">{practiceKindLabel(recData, r)}</p>}
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-lg font-medium">{r.title}</h2>
                    {r.difficulty && <DifficultyBadge difficulty={r.difficulty as 'Easy' | 'Medium' | 'Hard'} />}
                  </div>
                  {r.pattern && <p className="mt-2 text-sm text-muted-foreground">Listed topic: {r.pattern.replace(/_/g, ' ')}</p>}
                  {r.topics && r.topics.length > 0 && <p className="mt-2 text-sm text-muted-foreground">Catalog topics: {r.topics.join(', ')}</p>}
                  {practiceReason(recData, r) && <p className="mt-2 max-w-xl text-sm text-muted-foreground">{practiceReason(recData, r)}</p>}
                </div>
                <div className="flex flex-wrap items-center gap-4">
                  <RecommendationLink url={r.problem_url} title={r.title} />
                  {isPracticePolicy(recData) && <button type="button"
                    aria-label={`Skip ${r.title}`} disabled={excludedIds.length >= 50} onClick={() => skip(r.problem_id)}
                    className="text-link min-h-11 min-w-11 rounded px-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:opacity-50">Skip</button>}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
