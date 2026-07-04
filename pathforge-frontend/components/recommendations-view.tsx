'use client'

import { useState } from 'react'
import { ArrowUpRight, Target, TrendingUp } from 'lucide-react'
import { Panel, PanelBody, PanelHeader, PanelTitle } from '@/components/ui/panel'
import { Badge } from '@/components/ui/badge'
import { Meter } from '@/components/charts'
import { StatTile } from '@/components/ui/stat'
import { DifficultyBadge } from '@/components/dashboard'
import { cn } from '@/lib/utils'
import { useRecommendations } from '@/hooks/useApi'
import { useAuth } from '@/auth/AuthProvider'

const FILTERS = ['All', 'Easy', 'Medium', 'Hard'] as const

export function RecommendationsView() {
  const { profile } = useAuth()
  const { data: recData, loading } = useRecommendations(profile?.user_id ?? 0)
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>('All')

  const items = recData?.recommendations ?? []
  const list = items.filter(
    (r) => filter === 'All' || r.difficulty === filter,
  )
  const totalGain = items.reduce((s, r) => s + (r.score ?? 0), 0)

  if (loading) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-lg font-semibold tracking-tight">Recommendations</h1>
        <p className="text-sm text-muted-foreground">Loading recommendations...</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Recommendations</h1>
          <p className="text-sm text-muted-foreground">
            Ranked by the recommendation engine to maximize Elo gain on weak patterns.
          </p>
        </div>
        <div className="flex gap-1 rounded-md border border-border bg-card p-0.5">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                'rounded px-2.5 py-1 text-xs font-medium transition-colors',
                filter === f ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Queued" value={items.length} icon={Target} accent />
        <StatTile label="Potential Gain" value={`+${Math.round(totalGain)}`} icon={TrendingUp} sub={<span className="text-success">est. total</span>} />
        <StatTile label="Avg Match" value={items.length > 0 ? `${Math.round(items.reduce((s, r) => s + (r.score ?? 0), 0) / items.length)}%` : '-'} />
        <StatTile label="Hard Targets" value={items.filter((r) => r.difficulty === 'Hard').length} />
      </div>

      <div className="flex flex-col gap-3">
        {list.length === 0 && (
          <Panel>
            <PanelBody className="text-center text-sm text-muted-foreground">
              No recommendations available. Submit code to generate recommendations.
            </PanelBody>
          </Panel>
        )}
        {list.map((r, i) => (
          <Panel key={r.problem_id ?? i} className="transition-colors hover:border-primary/40">
            <div className="flex flex-col gap-3 p-4 md:flex-row md:items-center">
              <div className="flex items-center gap-3">
                <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-secondary font-mono text-xs text-muted-foreground">
                  {i + 1}
                </span>
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[10px] text-muted-foreground">{r.problem_id}</span>
                  <h3 className="text-sm font-medium">{r.title}</h3>
                  {r.difficulty && (
                    <DifficultyBadge difficulty={r.difficulty as 'Easy' | 'Medium' | 'Hard'} />
                  )}
                </div>
                {r.reason && (
                  <p className="mt-1 text-xs text-muted-foreground">{r.reason}</p>
                )}
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  <span className="font-mono text-[10px] uppercase text-muted-foreground">target</span>
                  <Badge key={r.pattern} variant="accent">
                    {r.pattern.replace(/_/g, ' ')}
                  </Badge>
                </div>
              </div>

              <div className="flex items-center gap-5 md:gap-6">
                {r.score != null && (
                  <>
                    <div className="w-28">
                      <div className="mb-1 flex items-center justify-between font-mono text-[10px] text-muted-foreground">
                        <span>match</span>
                        <span>{Math.round(r.score)}%</span>
                      </div>
                      <Meter value={Math.round(r.score)} />
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-lg font-semibold tabular-nums text-success">
                        +{Math.round(r.score)}
                      </p>
                      <p className="font-mono text-[10px] uppercase text-muted-foreground">score</p>
                    </div>
                  </>
                )}
                <button className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90">
                  Solve
                  <ArrowUpRight className="size-4" />
                </button>
              </div>
            </div>
          </Panel>
        ))}
      </div>
    </div>
  )
}
