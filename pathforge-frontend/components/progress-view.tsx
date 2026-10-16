'use client'

import Link from 'next/link'
import { useState } from 'react'
import { ArrowRight, ChartNoAxesCombined, Compass, Search } from 'lucide-react'
import { useAuth } from '@/auth/AuthProvider'
import { useAuthProfile, useEloData } from '@/hooks/useApi'
import { PracticeFootprint } from '@/components/practice-footprint'
import { cn, relativeTime } from '@/lib/utils'

export function ProgressView() {
  const { profile } = useAuth()
  const elo = useEloData(profile?.user_id ?? 0)
  const history = useAuthProfile()
  const [selected, setSelected] = useState<string | null>(null)
  const [chosen, setChosen] = useState<string[] | null>(null)
  const [query, setQuery] = useState('')
  const topics = new Map((history.data?.profiles ?? []).map(p => [p.topic, p]))
  const patterns = [...new Set([...Object.keys(elo.data?.pattern_elo ?? {}), ...topics.keys()])].sort()
  const active = selected && patterns.includes(selected) ? selected : patterns[0]
  const included = (chosen ?? patterns.slice(0, 3)).filter(id => patterns.includes(id))
  const filtered = patterns.filter(id => id.replace(/_/g, ' ').toLowerCase().includes(query.trim().toLowerCase()))
  const record = active ? topics.get(active) : undefined
  const rating = active ? elo.data?.pattern_elo[active] : undefined
  const loading = elo.loading || history.loading
  const error = elo.error || history.error
  const toggle = (id: string) => {
    setSelected(id)
    setChosen(previous => {
      const current = previous ?? patterns.slice(0, 3)
      return current.includes(id) ? current.filter(value => value !== id) : current.length < 4 ? [...current, id] : current
    })
  }

  return (
    <div className="workspace-page">
      <header className="page-intro">
        <p className="workspace-kicker flex items-center gap-2"><ChartNoAxesCombined className="size-4 text-mint" />Your practice notebook</p>
        <h1 className="page-heading">Learning Progress</h1>
        <p className="page-description">Choose the topics you want to see. Keep the next step in focus.</p>
      </header>
      {loading ? <p role="status" className="text-muted-foreground">Loading your practice history...</p> : error ? (
        <div className="border-t border-border py-6">
          <p role="alert">Could not load your practice history. {error}</p>
          <button type="button" onClick={() => { elo.refresh(); history.refresh() }} className="action-secondary mt-4">Retry history</button>
        </div>
      ) : patterns.length === 0 ? (
        <section className="flex flex-col gap-6 border-y border-border py-7 sm:flex-row sm:items-center sm:justify-between">
          <div><Compass className="mb-5 size-9 text-mint" /><h2 className="text-2xl font-medium tracking-tight">Your notebook starts with a solution.</h2>
          <p className="mt-3 max-w-xl text-base text-muted-foreground">Analyze Python code to start a record of the patterns you practise. There is no skill ranking to fill in first.</p></div>
          <Link href="/analysis" className="action-primary shrink-0">Analyze a solution <ArrowRight className="size-4" /></Link>
        </section>
      ) : <>
        <div className="grid min-w-0 gap-8 border-y border-border py-6 lg:grid-cols-[1.5fr_1fr]">
          <section className="min-w-0" aria-labelledby="footprint-heading">
            <div className="flex items-center justify-between gap-3"><h2 id="footprint-heading" className="section-title flex items-center gap-2"><ChartNoAxesCombined className="size-4 text-mint" />Practice footprint</h2><span className="text-[11px] text-muted-foreground">Your selection</span></div>
            <div className="pt-7"><PracticeFootprint records={history.data?.profiles ?? []} selected={included} /></div>
          </section>
          <section className="flex flex-col lg:border-l lg:border-border lg:pl-8" aria-labelledby="focus-heading" aria-live="polite">
            <p className="eyebrow text-amber"><Compass className="size-4" />Choose your own focus</p>
            <div key={active} className="detail-enter"><h2 id="focus-heading" className="mt-4 text-2xl font-semibold capitalize tracking-tight">{active.replace(/_/g, ' ')}</h2>
            <p className="mt-2 text-xs text-muted-foreground">{record?.last_attempt_at ? 'Last recorded ' + relativeTime(record.last_attempt_at) + '.' : 'A pattern in your saved practice record.'}</p></div>
            <h3 className="mt-7 text-sm font-semibold">Try a different implementation</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">Compare how two solutions express this pattern, including where the evidence is inconclusive.</p>
            <Link href="/analysis" className="action-primary mt-6 self-start">Inspect another solution <ArrowRight className="size-4" /></Link>
            <Link href="/recommendations" className="text-link mt-3 self-start">Browse practice <ArrowRight className="size-3.5" /></Link>
          </section>
        </div>
        <section className="min-w-0" aria-labelledby="patterns-heading">
          <div className="flex flex-wrap items-center justify-between gap-4"><div><h2 id="patterns-heading" className="section-title">Recorded patterns</h2><p id="topic-limit" className="mt-1 text-xs text-muted-foreground">Choose up to four topics for the chart. This list is alphabetical.</p></div>
            <div className="relative"><Search className="pointer-events-none absolute left-3 top-3 size-4 text-muted-foreground" /><input aria-label="Find a recorded topic" value={query} onChange={event => setQuery(event.target.value)} placeholder="Find a topic…" className="min-h-10 w-full rounded-md border border-input bg-card pl-9 pr-3 text-sm sm:w-60" /></div>
          </div>
          <div className="mt-5 grid max-h-64 gap-2 overflow-y-auto pr-1 sm:grid-cols-2 xl:grid-cols-3" role="group" aria-label="Topics in practice chart" aria-describedby="topic-limit">
            {filtered.map(id => <button key={id} type="button" onClick={() => toggle(id)} aria-pressed={included.includes(id)}
              disabled={!included.includes(id) && included.length >= 4}
              className={cn('flex min-h-11 items-center gap-3 border-b border-border px-2 py-2 text-left text-xs capitalize transition-colors disabled:cursor-not-allowed disabled:opacity-45', included.includes(id) ? 'bg-secondary/40 text-foreground' : 'text-muted-foreground hover:bg-secondary/40')}>
              <span className={cn('size-2 shrink-0 rounded-full', included.includes(id) ? 'bg-mint' : 'bg-muted-foreground/30')} />{id.replace(/_/g, ' ')}<span className="ml-auto text-base" aria-hidden="true">{included.includes(id) ? '−' : '+'}</span>
            </button>)}
          </div>
          {!filtered.length && <p role="status" className="mt-5 text-sm text-muted-foreground">No recorded topics match that search.</p>}
        </section>
        <details className="border-t border-border py-4">
          <summary className="cursor-pointer text-sm font-medium">Recorded metrics</summary>
          <p className="mt-3 text-xs text-muted-foreground">Stored engine metrics are not a correctness grade or a proficiency certification.</p>
          <dl className="mt-4 grid grid-cols-2 gap-5 text-sm sm:grid-cols-4">
            <div><dt className="text-muted-foreground">Pattern Elo</dt><dd className="mt-1 font-mono">{rating === undefined ? 'Not recorded' : Math.round(rating)}</dd></div>
            <div><dt className="text-muted-foreground">Pattern attempts</dt><dd className="mt-1 font-mono">{record?.attempt_count ?? 'Not recorded'}</dd></div>
            <div><dt className="text-muted-foreground">Stored pass count</dt><dd className="mt-1 font-mono">{record?.pass_count ?? 'Not recorded'}</dd></div>
            <div><dt className="text-muted-foreground">Stored accuracy</dt><dd className="mt-1 font-mono">{record && record.attempt_count > 0 ? Math.round(record.accuracy * 100) + '%' : 'Not recorded'}</dd></div>
          </dl>
          <p className="mt-4 text-xs text-muted-foreground">Rating history is not retained, so a progress-over-time chart is unavailable.</p>
        </details>
      </>}
    </div>
  )
}
