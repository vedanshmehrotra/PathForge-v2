'use client'

import Link from 'next/link'
import { ArrowRight, BarChart3, History, Play, Target, TrendingUp } from 'lucide-react'
import { Panel, PanelBody, PanelHeader, PanelTitle } from '@/components/ui/panel'
import { Badge } from '@/components/ui/badge'
import { Meter } from '@/components/charts'
import { StatTile } from '@/components/ui/stat'
import { cn, relativeTime } from '@/lib/utils'
import { useAuthProfile, useEloData, useRecommendations } from '@/hooks/useApi'
import { useAuth } from '@/auth/AuthProvider'
import { ELO_METER_MAX, skillStatus, type PatternSkill } from '@/services/skill'

const SNAPSHOT_LIMIT = 6
const ACTIVITY_LIMIT = 5

function toEntries(patternElo: Record<string, number> | undefined): PatternSkill[] {
  if (!patternElo) return []
  return Object.entries(patternElo)
    .map(([id, elo]) => ({ id, name: id.replace(/_/g, ' '), elo, status: skillStatus(elo) }))
    .sort((a, b) => b.elo - a.elo)
}

export function DifficultyBadge({ difficulty }: { difficulty: 'Easy' | 'Medium' | 'Hard' }) {
  const variant = difficulty === 'Easy' ? 'success' : difficulty === 'Medium' ? 'warning' : 'danger'
  return <Badge variant={variant}>{difficulty}</Badge>
}

export function DashboardView() {
  const { profile } = useAuth()
  const { data: eloData, loading: eloLoading } = useEloData(profile?.user_id ?? 0)
  const { data: authProfile, loading: profileLoading } = useAuthProfile()

  const entries = toEntries(eloData?.pattern_elo)
  const averageElo = entries.length
    ? Math.round(entries.reduce((s, e) => s + e.elo, 0) / entries.length)
    : 0
  // Below-average is the same relative split used on the Learning Progress page.
  const needsPractice = entries.filter((e) => e.elo < averageElo).length
  const attempts = (authProfile?.profiles ?? []).reduce((s, p) => s + (p.attempt_count ?? 0), 0)
  const hasElo = entries.length > 0

  const activity = [...(authProfile?.profiles ?? [])]
    .filter((p) => p.last_attempt_at || p.attempt_count > 0)
    .sort((a, b) => {
      const at = a.last_attempt_at ? new Date(a.last_attempt_at).getTime() : 0
      const bt = b.last_attempt_at ? new Date(b.last_attempt_at).getTime() : 0
      return bt - at
    })
    .slice(0, ACTIVITY_LIMIT)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Where your practice stands and what to work on next.
          </p>
        </div>
        <Link
          href="/analysis"
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          <Play className="size-4" />
          Analyze a solution
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile
          label="Patterns Tracked"
          value={hasElo ? entries.length : '\u2014'}
          icon={BarChart3}
          sub={hasElo ? undefined : 'No patterns yet'}
        />
        <StatTile
          label="Average Elo"
          value={hasElo ? averageElo : '\u2014'}
          sub={hasElo ? undefined : 'Analyze a solution'}
        />
        <StatTile
          label="Needs Practice"
          value={hasElo ? needsPractice : '\u2014'}
          sub={hasElo ? <span className="text-warning">below your average</span> : undefined}
        />
        <StatTile
          label="Recorded Attempts"
          value={attempts > 0 ? attempts : '\u2014'}
          sub={attempts > 0 ? undefined : 'No submissions yet'}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Panel>
          <PanelHeader>
            <PanelTitle>
              <History className="size-4 text-primary" />
              Recent Pattern Activity
            </PanelTitle>
            <span className="font-mono text-[10px] text-muted-foreground">
              {activity.length} / {entries.length} patterns
            </span>
          </PanelHeader>
          <div className={cn('divide-y divide-border', profileLoading && 'opacity-50')}>
            {!profileLoading && activity.length === 0 && (
              <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                No practice recorded yet. Analyze a solution to start tracking your patterns.
              </div>
            )}
            {activity.map((p) => (
              <div key={p.topic} className="flex items-center gap-3 px-4 py-2.5">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm">{p.topic.replace(/_/g, ' ')}</p>
                  <p className="font-mono text-[10px] text-muted-foreground">
                    {p.attempt_count} attempts &middot; {p.pass_count} confirmed
                    {p.accuracy > 0 && ` \u00b7 ${Math.round(p.accuracy * 100)}% accuracy`}
                  </p>
                </div>
                <span className="font-mono text-xs tabular-nums text-muted-foreground">
                  {Math.round(p.elo_rating)}
                </span>
                <span className="w-16 text-right font-mono text-[10px] text-muted-foreground">
                  {relativeTime(p.last_attempt_at)}
                </span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel>
          <PanelHeader>
            <PanelTitle>
              <TrendingUp className="size-4 text-primary" />
              Skill Snapshot
            </PanelTitle>
            <Link href="/progress" className="font-mono text-[10px] text-primary hover:underline">
              full breakdown
            </Link>
          </PanelHeader>
          <div className={cn('divide-y divide-border', eloLoading && 'opacity-50')}>
            {!eloLoading && entries.length === 0 && (
              <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                No Elo data yet. Submit code to initialize your pattern ratings.
              </div>
            )}
            {entries.slice(0, SNAPSHOT_LIMIT).map((e) => (
              <div key={e.id} className="flex items-center gap-3 px-4 py-2.5">
                <div className="w-40 shrink-0">
                  <p className="truncate text-sm">{e.name}</p>
                </div>
                <div className="min-w-0 flex-1">
                  <Meter value={e.elo} max={ELO_METER_MAX} />
                </div>
                <span className="w-12 text-right font-mono text-sm tabular-nums">
                  {Math.round(e.elo)}
                </span>
              </div>
            ))}
            {entries.length > SNAPSHOT_LIMIT && (
              <div className="px-4 py-2 text-right">
                <Link href="/progress" className="font-mono text-[10px] text-primary hover:underline">
                  +{entries.length - SNAPSHOT_LIMIT} more patterns
                </Link>
              </div>
            )}
          </div>
        </Panel>
      </div>

      <RecommendedPreview />
    </div>
  )
}

export function RecommendedPreview() {
  const { profile } = useAuth()
  const { data: recData, loading } = useRecommendations(profile?.user_id ?? 0)

  const items = (recData?.recommendations ?? []).slice(0, 2)

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
          all recommendations <ArrowRight className="size-3" />
        </Link>
      </PanelHeader>
      {loading && (
        <PanelBody className="text-center text-sm text-muted-foreground">Loading...</PanelBody>
      )}
      {!loading && items.length === 0 && (
        <PanelBody className="text-center text-sm text-muted-foreground">
          No recommendations yet. Analyze a solution to generate a practice queue.
        </PanelBody>
      )}
      {!loading && items.length > 0 && (
        <div className="divide-y divide-border">
          {items.map((r) => (
            <div key={r.problem_id} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[10px] text-muted-foreground">{r.problem_id}</span>
                  <p className="truncate text-sm font-medium">{r.title}</p>
                  {r.difficulty && (
                    <DifficultyBadge difficulty={r.difficulty as 'Easy' | 'Medium' | 'Hard'} />
                  )}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Target: {r.pattern.replace(/_/g, ' ')}
                  {r.score != null && (
                    <span className="ml-2 font-mono text-success">+{Math.round(r.score)} expected gain</span>
                  )}
                </p>
              </div>
              <Link
                href="/recommendations"
                className="inline-flex items-center gap-1 rounded-md bg-secondary px-3 py-1.5 text-xs font-medium text-secondary-foreground transition-opacity hover:opacity-80"
              >
                Solve <ArrowRight className="size-3" />
              </Link>
            </div>
          ))}
        </div>
      )}
    </Panel>
  )
}
