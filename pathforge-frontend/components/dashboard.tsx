'use client'

import Link from 'next/link'
import { ArrowRight, CheckCircle2, CircleSlash, MinusCircle, Target, TriangleAlert } from 'lucide-react'
import { Panel, PanelHeader, PanelTitle } from '@/components/ui/panel'
import { Badge } from '@/components/ui/badge'
import { Meter } from '@/components/charts'
import { cn } from '@/lib/utils'
import { useEloData, useRecommendations } from '@/hooks/useApi'
import { useAuth } from '@/auth/AuthProvider'

export function CategoryElo() {
  const { profile } = useAuth()
  const { data: eloData, loading } = useEloData(profile?.user_id ?? 0)

  const entries = eloData?.pattern_elo
    ? Object.entries(eloData.pattern_elo)
        .map(([name, elo]) => ({ name, elo }))
        .sort((a, b) => b.elo - a.elo)
    : []

  if (loading || !entries.length) {
    return (
      <Panel>
        <PanelHeader>
          <PanelTitle>Elo by Pattern Category</PanelTitle>
        </PanelHeader>
        <div className="px-4 py-6 text-center text-sm text-muted-foreground">
          {loading ? 'Loading...' : 'No Elo data yet. Submit code to initialize.'}
        </div>
      </Panel>
    )
  }

  return (
    <Panel>
      <PanelHeader>
        <PanelTitle>Elo by Pattern Category</PanelTitle>
        <span className="font-mono text-[10px] text-muted-foreground">
          {entries.length} patterns
        </span>
      </PanelHeader>
      <div className="divide-y divide-border">
        {entries.map((c) => (
          <div key={c.name} className="flex items-center gap-3 px-4 py-2.5">
            <div className="w-40 shrink-0">
              <p className="truncate text-sm">{c.name.replace(/_/g, ' ')}</p>
            </div>
            <div className="flex-1">
              <Meter value={c.elo} max={2200} />
            </div>
            <span className="w-14 text-right font-mono text-sm tabular-nums">
              {Math.round(c.elo)}
            </span>
          </div>
        ))}
      </div>
    </Panel>
  )
}

export function WeakestPatterns() {
  const { profile } = useAuth()
  const { data: eloData, loading } = useEloData(profile?.user_id ?? 0)

  const weakest = eloData?.summary?.weakest_patterns ?? []

  return (
    <Panel>
      <PanelHeader>
        <PanelTitle>
          <TriangleAlert className="size-4 text-warning" />
          Weakest Patterns
        </PanelTitle>
        <Link href="/progress" className="font-mono text-[10px] text-primary hover:underline">
          view all
        </Link>
      </PanelHeader>
      <div className="divide-y divide-border">
        {loading && (
          <div className="px-4 py-6 text-center text-sm text-muted-foreground">Loading...</div>
        )}
        {!loading && weakest.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-muted-foreground">
            No data yet
          </div>
        )}
        {weakest.map((name, i) => (
          <div key={name} className="flex items-center gap-3 px-4 py-3">
            <span className="font-mono text-xs text-muted-foreground">#{i + 1}</span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm">{name.replace(/_/g, ' ')}</p>
            </div>
            <span className="font-mono text-sm tabular-nums">
              {eloData?.pattern_elo ? Math.round(eloData.pattern_elo[name]) : '-'}
            </span>
          </div>
        ))}
      </div>
    </Panel>
  )
}

export function RecommendedPreview() {
  const { profile } = useAuth()
  const { data: recData, loading } = useRecommendations(profile?.user_id ?? 0)

  const items = recData?.recommendations ?? []

  return (
    <Panel>
      <PanelHeader>
        <PanelTitle>
          <Target className="size-4 text-primary" />
          Recommended Next
        </PanelTitle>
        <Link
          href="/recommendations"
          className="flex items-center gap-1 font-mono text-[10px] text-primary hover:underline"
        >
          all <ArrowRight className="size-3" />
        </Link>
      </PanelHeader>
      <div className="divide-y divide-border">
        {loading && (
          <div className="px-4 py-6 text-center text-sm text-muted-foreground">Loading...</div>
        )}
        {!loading && items.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-muted-foreground">
            No recommendations yet
          </div>
        )}
        {items.slice(0, 4).map((r) => (
          <div key={r.problem_id} className="flex items-center gap-3 px-4 py-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] text-muted-foreground">{r.problem_id}</span>
                <p className="truncate text-sm font-medium">{r.title}</p>
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                <Badge variant="default">
                  {r.pattern.replace(/_/g, ' ')}
                </Badge>
              </div>
            </div>
            <DifficultyBadge difficulty={r.difficulty as 'Easy' | 'Medium' | 'Hard'} />
            {r.score && (
              <div className="w-16 text-right">
                <div className="font-mono text-sm tabular-nums text-success">+{Math.round(r.score)}</div>
                <div className="font-mono text-[10px] text-muted-foreground">score</div>
              </div>
            )}
          </div>
        ))}
      </div>
    </Panel>
  )
}

export function DifficultyBadge({ difficulty }: { difficulty: 'Easy' | 'Medium' | 'Hard' }) {
  const variant = difficulty === 'Easy' ? 'success' : difficulty === 'Medium' ? 'warning' : 'danger'
  return <Badge variant={variant}>{difficulty}</Badge>
}

const RESULT_META = {
  solved: { icon: CheckCircle2, color: 'text-success' },
  failed: { icon: CircleSlash, color: 'text-destructive' },
  partial: { icon: MinusCircle, color: 'text-warning' },
} as const

interface ActivityItem {
  id: string
  problem: string
  result: 'solved' | 'failed' | 'partial'
  patterns: string[]
  eloChange: number
  time: string
}

function ActivityRow({ a }: { a: ActivityItem }) {
  const meta = RESULT_META[a.result]
  const Icon = meta.icon
  return (
    <div className="flex items-center gap-3 px-4 py-2.5">
      <Icon className={cn('size-4 shrink-0', meta.color)} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] text-muted-foreground">{a.id}</span>
          <p className="truncate text-sm">{a.problem}</p>
        </div>
        <div className="mt-0.5 flex flex-wrap gap-1">
          {a.patterns.map((p) => (
            <span key={p} className="font-mono text-[10px] text-muted-foreground">
              {p}
            </span>
          ))}
        </div>
      </div>
      <span className="font-mono text-[10px] text-muted-foreground">{a.time}</span>
      <span
        className={cn(
          'w-12 text-right font-mono text-sm tabular-nums',
          a.eloChange > 0 ? 'text-success' : a.eloChange < 0 ? 'text-destructive' : 'text-muted-foreground',
        )}
      >
        {a.eloChange > 0 ? `+${a.eloChange}` : a.eloChange}
      </span>
    </div>
  )
}

export function ActivityFeed() {
  return (
    <Panel>
      <PanelHeader>
        <PanelTitle>Recent Activity</PanelTitle>
        <span className="font-mono text-[10px] text-muted-foreground">live feed</span>
      </PanelHeader>
      <div className="px-4 py-6 text-center text-sm text-muted-foreground">
        Submit code to see recent activity.
      </div>
    </Panel>
  )
}
