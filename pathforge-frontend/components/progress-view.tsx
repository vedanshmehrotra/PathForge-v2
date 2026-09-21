'use client'

import { useMemo, useState } from 'react'
import { ChevronRight, Layers, LineChart, Target, TrendingUp } from 'lucide-react'
import { Panel, PanelBody, PanelHeader, PanelTitle } from '@/components/ui/panel'
import { Badge } from '@/components/ui/badge'
import { Meter } from '@/components/charts'
import { StatTile } from '@/components/ui/stat'
import { cn, relativeTime } from '@/lib/utils'
import { useAuthProfile, useEloData } from '@/hooks/useApi'
import { useAuth } from '@/auth/AuthProvider'
import { ELO_METER_MAX, skillStatus, statusVariant, type PatternSkill } from '@/services/skill'
import type { AuthProfile } from '@/types/api'

type TopicProfile = AuthProfile['profiles'][number]

function PatternRow({
  pattern,
  active,
  onSelect,
}: {
  pattern: PatternSkill
  active: boolean
  onSelect: () => void
}) {
  return (
    <button
      onClick={onSelect}
      className={cn(
        'flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors',
        active ? 'bg-accent/50' : 'hover:bg-accent/30',
      )}
    >
      <div className="w-40 shrink-0">
        <p className="truncate text-sm">{pattern.name}</p>
      </div>
      <div className="min-w-0 flex-1">
        <Meter value={pattern.elo} max={ELO_METER_MAX} />
      </div>
      <span className="w-12 text-right font-mono text-sm tabular-nums">
        {Math.round(pattern.elo)}
      </span>
      <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" />
    </button>
  )
}

function DetailStat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span className="font-mono text-lg tabular-nums leading-none">{value}</span>
    </div>
  )
}

export function ProgressView() {
  const { profile } = useAuth()
  const { data: eloData, loading: eloLoading } = useEloData(profile?.user_id ?? 0)
  const { data: authProfile, loading: profileLoading } = useAuthProfile()

  const entries = useMemo<PatternSkill[]>(() => {
    if (!eloData?.pattern_elo) return []
    return Object.entries(eloData.pattern_elo)
      .map(([id, elo]) => ({ id, name: id.replace(/_/g, ' '), elo, status: skillStatus(elo) }))
      .sort((a, b) => b.elo - a.elo)
  }, [eloData])

  const topics = useMemo(() => {
    const map = new Map<string, TopicProfile>()
    for (const p of authProfile?.profiles ?? []) map.set(p.topic, p)
    return map
  }, [authProfile])

  const [selected, setSelected] = useState<string | null>(null)
  const active = entries.find((e) => e.id === selected) ?? entries[0]
  const activeTopic = active ? topics.get(active.id) : undefined

  const averageElo = entries.length
    ? Math.round(entries.reduce((s, e) => s + e.elo, 0) / entries.length)
    : 0
  const stronger = entries.filter((e) => e.elo >= averageElo)
  const weaker = entries.filter((e) => e.elo < averageElo)

  const lastPracticed = (authProfile?.profiles ?? [])
    .map((p) => p.last_attempt_at)
    .filter((v): v is string => Boolean(v))
    .sort()
    .pop()

  if (eloLoading) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-lg font-semibold tracking-tight">Learning Progress</h1>
        <p className="text-sm text-muted-foreground">Loading your pattern ratings...</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Learning Progress</h1>
        <p className="text-sm text-muted-foreground">
          What is stronger, what still needs practice, and where to focus next.
        </p>
      </div>

      {entries.length === 0 ? (
        <Panel>
          <PanelBody className="py-10 text-center">
            <TrendingUp className="mx-auto size-5 text-muted-foreground" />
            <p className="mt-3 text-sm font-medium">No patterns tracked yet.</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Analyze a solution and your pattern ratings will appear here.
            </p>
          </PanelBody>
        </Panel>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatTile label="Tracked Patterns" value={entries.length} icon={Layers} accent />
            <StatTile label="Average Elo" value={averageElo} />
            <StatTile
              label="Stronger Areas"
              value={stronger.length}
              sub={<span className="text-success">at or above average</span>}
            />
            <StatTile
              label="Needs Practice"
              value={weaker.length}
              sub={<span className="text-warning">below average</span>}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Panel>
              <PanelHeader>
                <PanelTitle>
                  <span className="size-2 rounded-full bg-success" />
                  Stronger Areas
                </PanelTitle>
                <span className="font-mono text-[10px] text-muted-foreground">
                  at or above {averageElo}
                </span>
              </PanelHeader>
              <div className="divide-y divide-border">
                {stronger.map((e) => (
                  <PatternRow
                    key={e.id}
                    pattern={e}
                    active={active?.id === e.id}
                    onSelect={() => setSelected(e.id)}
                  />
                ))}
              </div>
            </Panel>

            <Panel>
              <PanelHeader>
                <PanelTitle>
                  <span className="size-2 rounded-full bg-warning" />
                  Developing / Needs Practice
                </PanelTitle>
                <span className="font-mono text-[10px] text-muted-foreground">
                  below {averageElo}
                </span>
              </PanelHeader>
              <div className="divide-y divide-border">
                {weaker.length === 0 && (
                  <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                    Every tracked pattern is at or above your average.
                  </div>
                )}
                {weaker.map((e) => (
                  <PatternRow
                    key={e.id}
                    pattern={e}
                    active={active?.id === e.id}
                    onSelect={() => setSelected(e.id)}
                  />
                ))}
              </div>
            </Panel>
          </div>

          <Panel>
            <PanelHeader>
              <PanelTitle>
                <LineChart className="size-4 text-primary" />
                Recent Progress
              </PanelTitle>
              {lastPracticed && (
                <span className="font-mono text-[10px] text-muted-foreground">
                  last practice {relativeTime(lastPracticed)}
                </span>
              )}
            </PanelHeader>
            <PanelBody className="py-8 text-center">
              <p className="text-sm font-medium">Not enough submissions yet to show a trend.</p>
              <p className="mx-auto mt-1 max-w-md text-xs text-muted-foreground">
                Trend lines need a history of confirmed solutions per pattern. Keep analyzing and
                rating movement will appear here.
              </p>
            </PanelBody>
          </Panel>

          {active && (
            <Panel>
              <PanelHeader>
                <PanelTitle>
                  <Target className="size-4 text-primary" />
                  Pattern Detail
                </PanelTitle>
                <Badge variant={statusVariant(active.status)}>{active.status}</Badge>
              </PanelHeader>
              <PanelBody className="flex flex-col gap-5">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <span className="text-base font-medium capitalize">{active.name}</span>
                  <span className="font-mono text-xs text-muted-foreground">
                    {active.id.replace(/ /g, '_')}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-4 border-t border-border pt-4 sm:grid-cols-4">
                  <DetailStat label="Elo" value={Math.round(active.elo)} />
                  <DetailStat
                    label="Attempts"
                    value={activeTopic ? activeTopic.attempt_count : '\u2014'}
                  />
                  <DetailStat
                    label="Confirmed"
                    value={activeTopic ? activeTopic.pass_count : '\u2014'}
                  />
                  <DetailStat
                    label="Accuracy"
                    value={
                      activeTopic && activeTopic.attempt_count > 0
                        ? `${Math.round(activeTopic.accuracy * 100)}%`
                        : '\u2014'
                    }
                  />
                </div>
                <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-border pt-4 text-xs text-muted-foreground">
                  <span>
                    Recent failures:{' '}
                    <span className="font-mono text-foreground">
                      {activeTopic ? activeTopic.recent_failures : '\u2014'}
                    </span>
                  </span>
                  <span>
                    Last attempt:{' '}
                    <span className="font-mono text-foreground">
                      {relativeTime(activeTopic?.last_attempt_at)}
                    </span>
                  </span>
                </div>
                {!activeTopic && !profileLoading && (
                  <p className="text-xs text-muted-foreground">
                    No attempts recorded for this pattern yet.
                  </p>
                )}
                <p className="text-[11px] text-muted-foreground/80">
                  Per-pattern Elo history is not retained, so no movement chart is shown for this
                  pattern.
                </p>
              </PanelBody>
            </Panel>
          )}
        </>
      )}
    </div>
  )
}
