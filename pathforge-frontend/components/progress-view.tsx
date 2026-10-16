'use client'

import Link from 'next/link'
import { useState } from 'react'
import { ArrowRight, ChevronRight } from 'lucide-react'
import { useAuth } from '@/auth/AuthProvider'
import { useAuthProfile, useEloData } from '@/hooks/useApi'
import { cn, relativeTime } from '@/lib/utils'

export function ProgressView() {
  const { profile } = useAuth()
  const elo = useEloData(profile?.user_id ?? 0)
  const history = useAuthProfile()
  const [selected, setSelected] = useState<string | null>(null)
  const topics = new Map((history.data?.profiles ?? []).map(p => [p.topic, p]))
  // Alphabetical order is a browsing aid, not a proficiency ranking.
  const patterns = [...new Set([...Object.keys(elo.data?.pattern_elo ?? {}), ...topics.keys()])].sort()
  const active = selected && patterns.includes(selected) ? selected : patterns[0]
  const record = active ? topics.get(active) : undefined
  const rating = active ? elo.data?.pattern_elo[active] : undefined
  const loading = elo.loading || history.loading
  const error = elo.error || history.error

  return (
    <div className="workspace-page">
      <header className="page-intro">
        <p className="workspace-kicker">Your practice notebook</p>
        <h1 className="page-heading">Learning Progress</h1>
        <p className="page-description">Revisit recorded patterns and choose a focus for your next session.</p>
      </header>
      {loading ? <p role="status" className="text-muted-foreground">Loading your practice history...</p> : error ? (
        <div>
          <p role="alert">Could not load your practice history. {error}</p>
          <button type="button" onClick={() => { elo.refresh(); history.refresh() }} className="action-secondary mt-4">Retry history</button>
        </div>
      ) : patterns.length === 0 ? (
        <section className="border-y border-border py-10">
          <h2 className="text-2xl font-medium tracking-tight">Your notebook starts with a solution.</h2>
          <p className="mt-3 max-w-xl text-base text-muted-foreground">Analyze Python code to start a record of the patterns you practise. There is no skill ranking to fill in first.</p>
          <Link href="/analysis" className="action-primary mt-6">Analyze a solution <ArrowRight className="size-4" /></Link>
        </section>
      ) : (
        <div className="grid gap-8 border-t border-border pt-8 lg:grid-cols-[minmax(220px,1fr)_2fr] lg:gap-12">
          <section aria-labelledby="patterns-heading">
            <h2 id="patterns-heading" className="section-title">Recorded patterns</h2>
            <p className="mt-2 text-sm text-muted-foreground">Choose a pattern to revisit. This list is alphabetical.</p>
            <ul className="mt-5 divide-y divide-border">
              {patterns.map(id => (
                <li key={id}>
                  <button type="button" aria-pressed={active === id} onClick={() => setSelected(id)}
                    className={cn('flex min-h-12 w-full items-center justify-between gap-3 rounded px-2 py-3 text-left text-sm capitalize transition-colors', active === id ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:text-foreground')}>
                    <span>{id.replace(/_/g, ' ')}</span><ChevronRight className="size-4 shrink-0" />
                  </button>
                </li>
              ))}
            </ul>
          </section>
          <section aria-labelledby="focus-heading" aria-live="polite">
            <p className="workspace-kicker">Choose your own focus</p>
            <h2 id="focus-heading" className="mt-3 text-2xl font-medium capitalize tracking-tight">{active.replace(/_/g, ' ')}</h2>
            <p className="mt-3 text-sm text-muted-foreground">{record?.last_attempt_at ? 'Last recorded ' + relativeTime(record.last_attempt_at) + '.' : 'A pattern in your saved practice record.'}</p>
            <h3 className="section-title mt-8">Try a different implementation</h3>
            <p className="mt-3 max-w-xl text-base leading-relaxed text-muted-foreground">Compare how two solutions express this pattern. Use analysis to inspect the evidence, including the places it cannot draw a conclusion.</p>
            <Link href="/analysis" className="action-primary mt-6">Inspect another solution <ArrowRight className="size-4" /></Link>
            <Link href="/recommendations" className="text-link ml-0 mt-4 block w-fit sm:ml-5 sm:inline-flex">Browse practice</Link>
            <details className="mt-10 border-t border-border pt-5">
              <summary className="cursor-pointer text-sm font-medium">Recorded metrics</summary>
              <p className="mt-3 text-sm text-muted-foreground">Stored engine metrics are not a correctness grade or a proficiency certification.</p>
              <dl className="mt-4 grid grid-cols-2 gap-5 text-sm">
                <div><dt className="text-muted-foreground">Pattern Elo</dt><dd className="mt-1 font-mono">{rating === undefined ? 'Not recorded' : Math.round(rating)}</dd></div>
                <div><dt className="text-muted-foreground">Pattern attempts</dt><dd className="mt-1 font-mono">{record?.attempt_count ?? 'Not recorded'}</dd></div>
                <div><dt className="text-muted-foreground">Stored pass count</dt><dd className="mt-1 font-mono">{record?.pass_count ?? 'Not recorded'}</dd></div>
                <div><dt className="text-muted-foreground">Stored accuracy</dt><dd className="mt-1 font-mono">{record && record.attempt_count > 0 ? Math.round(record.accuracy * 100) + '%' : 'Not recorded'}</dd></div>
              </dl>
              <p className="mt-5 text-sm text-muted-foreground">Rating history is not retained, so a progress-over-time chart is unavailable.</p>
            </details>
          </section>
        </div>
      )}
    </div>
  )
}
