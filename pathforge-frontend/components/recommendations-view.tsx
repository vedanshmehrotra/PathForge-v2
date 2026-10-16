'use client'

import { useState } from 'react'
import { Panel, PanelBody } from '@/components/ui/panel'
import { DifficultyBadge } from '@/components/dashboard'
import { RecommendationLink } from '@/components/recommendation-link'
import { cn } from '@/lib/utils'
import { useRecommendations } from '@/hooks/useApi'
import { useAuth } from '@/auth/AuthProvider'
import { practiceEmptyMessage, practiceReason, uniqueRecommendations } from '@/services/recommendations'

const FILTERS = ['All', 'Easy', 'Medium', 'Hard'] as const

export function RecommendationsView() {
  const { profile } = useAuth()
  return <PracticeSuggestions key={profile?.user_id ?? 0} userId={profile?.user_id ?? 0} />
}

function PracticeSuggestions({ userId }: { userId: number }) {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>('All')
  const [excludedIds, setExcludedIds] = useState<string[]>([])
  const { data: recData, loading, error, refresh } = useRecommendations(
    userId, filter === 'All' ? undefined : filter, excludedIds,
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
          <p className="mt-3 max-w-xl text-sm text-muted-foreground">{recData?.policy === 'recorded_practice_v1'
            ? 'Suggestions use your recorded practice to offer variety and older revisits. No topic selection is required. They do not establish correctness or mastery.'
            : 'Choices from the current problem bank. These do not establish correctness or mastery.'}</p>
          {recData?.history?.truncated && <p className="mt-2 text-sm text-muted-foreground">Using only your latest recorded submissions; older practice may not be represented.</p>}
          {!!recData?.history?.unmapped_submissions && <p className="mt-2 text-sm text-muted-foreground">Some recorded problems could not be linked to the current bank.</p>}
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
        <span className="text-muted-foreground">Skips last until you leave this page.</span>
        <button type="button" onClick={() => setExcludedIds([])} className="text-link">Reset skips</button>
      </div>}

      {loading ? <p role="status" className="text-sm text-muted-foreground">Loading practice suggestions...</p> : error ? (
        <Panel><PanelBody>
          <p role="alert" className="text-sm">Could not load practice suggestions. {error}</p>
          <button type="button" onClick={refresh} className="mt-3 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground">Retry</button>
        </PanelBody></Panel>
      ) : items.length === 0 ? (
        <Panel><PanelBody>
          <p role="status" className="text-sm text-muted-foreground">{practiceEmptyMessage(recData?.state)}</p>
          <button type="button" onClick={refresh} className="mt-3 text-sm text-primary underline">Refresh suggestions</button>
        </PanelBody></Panel>
      ) : list.length === 0 ? (
        <Panel><PanelBody>
          <p className="text-sm text-muted-foreground">No {filter} suggestions are in this list. Choose another difficulty.</p>
          <button type="button" onClick={() => setFilter('All')} className="mt-3 text-sm text-primary underline">Clear difficulty filter</button>
        </PanelBody></Panel>
      ) : (
        <div className="divide-y divide-border border-y border-border">
          {list.map(r => (
            <article key={r.problem_id}>
              <div className="flex flex-col gap-4 py-6 md:flex-row md:items-center">
                <div className="min-w-0 flex-1">
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
                  {recData?.policy === 'recorded_practice_v1' && <button type="button"
                    aria-label={`Skip ${r.title}`} disabled={excludedIds.length >= 50}
                    onClick={() => setExcludedIds(previous => [...previous, r.problem_id])}
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
