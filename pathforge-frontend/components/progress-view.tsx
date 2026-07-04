'use client'

import { useState } from 'react'
import { LineChart, Layers } from 'lucide-react'
import { Panel, PanelBody, PanelHeader, PanelTitle } from '@/components/ui/panel'
import { Badge } from '@/components/ui/badge'
import { TrendPill } from '@/components/charts'
import { StatTile } from '@/components/ui/stat'
import { cn } from '@/lib/utils'
import { useEloData } from '@/hooks/useApi'
import { useAuth } from '@/auth/AuthProvider'

export function ProgressView() {
  const { profile } = useAuth()
  const { data: eloData, loading } = useEloData(profile?.user_id ?? 0)

  const entries = eloData?.pattern_elo
    ? Object.entries(eloData.pattern_elo)
        .map(([id, elo]) => ({
          id,
          name: id.replace(/_/g, ' '),
          elo,
        }))
        .sort((a, b) => b.elo - a.elo)
    : []

  const [selected, setSelected] = useState<string | null>(entries[0]?.id ?? null)
  const active = entries.find((e) => e.id === selected) ?? entries[0]

  const strongCount = entries.filter((e) => e.elo >= 1800).length
  const weakCount = entries.filter((e) => e.elo < 1650).length
  const avgElo = entries.length
    ? Math.round(entries.reduce((s, e) => s + e.elo, 0) / entries.length)
    : 0

  if (loading) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-lg font-semibold tracking-tight">Learning Progress</h1>
        <p className="text-sm text-muted-foreground">Loading Elo data...</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Learning Progress</h1>
        <p className="text-sm text-muted-foreground">
          Elo trajectory, improvement trends, and skill clustering across all tracked patterns.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Tracked Patterns" value={entries.length} icon={Layers} />
        <StatTile label="Strong" value={strongCount} sub={<span className="text-success">Elo \u2265 1800</span>} />
        <StatTile label="Weak" value={weakCount} sub={<span className="text-destructive">Elo &lt; 1650</span>} />
        <StatTile label="Avg Elo" value={avgElo} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel className="lg:col-span-2">
          <PanelHeader>
            <PanelTitle>
              <LineChart className="size-4 text-primary" />
              Pattern Detail
            </PanelTitle>
          </PanelHeader>
          <PanelBody>
            {!active && (
              <p className="text-sm text-muted-foreground">No pattern data yet.</p>
            )}
            {active && (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <span className="font-mono text-lg tabular-nums">{active.name}</span>
                  <span className="font-mono text-lg tabular-nums text-primary">{Math.round(active.elo)}</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Select a pattern from the panel to view its details. Historical chart data will be
                  available after multiple submissions.
                </p>
              </div>
            )}
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader>
            <PanelTitle>Select Pattern</PanelTitle>
          </PanelHeader>
          <div className="max-h-[320px] divide-y divide-border overflow-y-auto">
            {entries.length === 0 && (
              <div className="px-4 py-6 text-center text-sm text-muted-foreground">
                No patterns tracked yet.
              </div>
            )}
            {entries.map((e) => (
              <button
                key={e.id}
                onClick={() => setSelected(e.id)}
                className={cn(
                  'flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors hover:bg-accent/50',
                  selected === e.id && 'bg-accent/60',
                )}
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm">{e.name}</p>
                </div>
                <span className="w-10 text-right font-mono text-xs tabular-nums">{Math.round(e.elo)}</span>
              </button>
            ))}
          </div>
        </Panel>
      </div>

      <Panel>
        <PanelHeader>
          <PanelTitle>Pattern Progression</PanelTitle>
          <span className="font-mono text-[10px] text-muted-foreground">{entries.length} rows</span>
        </PanelHeader>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                <th className="px-4 py-2 font-medium">Pattern</th>
                <th className="px-4 py-2 text-right font-medium">Elo</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {entries.map((e) => (
                <tr key={e.id} className="hover:bg-accent/30">
                  <td className="px-4 py-2.5">{e.name}</td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums">{Math.round(e.elo)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Panel>
          <PanelHeader>
            <PanelTitle>
              <span className="size-2 rounded-full bg-success" />
              Strong Cluster
            </PanelTitle>
            <span className="font-mono text-[10px] text-muted-foreground">Elo \u2265 1800</span>
          </PanelHeader>
          <div className="flex flex-wrap gap-2 p-4">
            {entries.filter((e) => e.elo >= 1800).length === 0 && (
              <p className="text-sm text-muted-foreground">No strong patterns yet.</p>
            )}
            {entries.filter((e) => e.elo >= 1800).map((e) => (
              <div key={e.id} className="flex items-center gap-2 rounded-md border border-success/25 bg-success/5 px-2.5 py-1.5">
                <span className="text-xs">{e.name}</span>
                <span className="font-mono text-xs tabular-nums text-success">{Math.round(e.elo)}</span>
              </div>
            ))}
          </div>
        </Panel>
        <Panel>
          <PanelHeader>
            <PanelTitle>
              <span className="size-2 rounded-full bg-destructive" />
              Weak Cluster
            </PanelTitle>
            <span className="font-mono text-[10px] text-muted-foreground">Elo &lt; 1650</span>
          </PanelHeader>
          <div className="flex flex-wrap gap-2 p-4">
            {entries.filter((e) => e.elo < 1650).length === 0 && (
              <p className="text-sm text-muted-foreground">No weak patterns.</p>
            )}
            {entries.filter((e) => e.elo < 1650).map((e) => (
              <div key={e.id} className="flex items-center gap-2 rounded-md border border-destructive/25 bg-destructive/5 px-2.5 py-1.5">
                <span className="text-xs">{e.name}</span>
                <span className="font-mono text-xs tabular-nums text-destructive">{Math.round(e.elo)}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  )
}
