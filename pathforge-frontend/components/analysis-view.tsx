'use client'

import { useState } from 'react'
import { Check, Cpu, GitCompare, Play, ScanLine, TriangleAlert, X, Zap } from 'lucide-react'
import { Panel, PanelBody, PanelHeader, PanelTitle } from '@/components/ui/panel'
import { Badge } from '@/components/ui/badge'
import { Meter } from '@/components/charts'
import { cn } from '@/lib/utils'
import { useAnalyzeCode } from '@/hooks/useApi'
import { useAuth } from '@/auth/AuthProvider'
import { useGapData, useEloData } from '@/hooks/useApi'

const SEVERITY = {
  high: { variant: 'danger' as const, label: 'HIGH' },
  medium: { variant: 'warning' as const, label: 'MED' },
  low: { variant: 'default' as const, label: 'LOW' },
} as const

export function AnalysisView() {
  const { profile } = useAuth()
  const [code, setCode] = useState('')

  const { result, loading, error, run } = useAnalyzeCode()
  const { data: gapData } = useGapData(profile?.user_id ?? 0)
  const { data: eloData } = useEloData(profile?.user_id ?? 0)

  const handleRun = () => {
    if (profile) {
      run({ user_id: String(profile.user_id), code, language: 'python' })
    }
  }

  const detectedPatterns = result?.ast?.detected_patterns as Array<{
    pattern_id?: string
    name?: string
    category?: string
    confidence?: number
    nodes?: number
    expected?: boolean
  }> | undefined

  const matchResult = result?.match_result as Record<string, unknown> | undefined
  const matchScore = matchResult?.overall_match as number ?? 0
  const matchedCount = (matchResult?.matched_patterns as unknown[])?.length ?? 0
  const divergentCount = (matchResult?.divergent_patterns as unknown[])?.length ?? 0
  const totalCount = matchedCount + divergentCount

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Code Analysis</h1>
          <p className="text-sm text-muted-foreground">
            Submit a solution to run the AST detector, matching engine, and gap analysis.
          </p>
        </div>
        <button
          onClick={handleRun}
          disabled={loading || !profile}
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
        >
          {loading ? <Cpu className="size-4 animate-pulse" /> : <Play className="size-4" />}
          {loading ? 'Analyzing\u2026' : 'Run Analysis'}
        </button>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <Panel>
            <PanelHeader>
              <PanelTitle>
                <ScanLine className="size-4 text-primary" />
                Solution Input
              </PanelTitle>
              <div className="flex items-center gap-2 font-mono text-[10px] text-muted-foreground">
                <span>python</span>
                <span>·</span>
                <span>{code.split('\n').length} lines</span>
              </div>
            </PanelHeader>
            <div className="flex">
              <div className="select-none border-r border-border bg-secondary/40 px-2 py-3 text-right font-mono text-xs leading-[1.6] text-muted-foreground/60">
                {code.split('\n').map((_, i) => (
                  <div key={i}>{i + 1}</div>
                ))}
              </div>
              <textarea
                value={code}
                onChange={(e) => setCode(e.target.value)}
                spellCheck={false}
                className="min-h-[360px] flex-1 resize-none bg-transparent px-3 py-3 font-mono text-xs leading-[1.6] text-foreground outline-none"
              />
            </div>
          </Panel>
        </div>

        <div className="flex flex-col gap-4 lg:col-span-2">
          <Panel>
            <PanelHeader>
              <PanelTitle>
                <Cpu className="size-4 text-primary" />
                AST Detected Patterns
              </PanelTitle>
              <span className="font-mono text-[10px] text-muted-foreground">
                {detectedPatterns?.length ?? 0} found
              </span>
            </PanelHeader>
            <div className={cn('divide-y divide-border transition-opacity', loading && 'opacity-40')}>
              {!detectedPatterns && (
                <div className="px-4 py-6 text-center text-sm text-muted-foreground">
                  Run analysis to detect patterns.
                </div>
              )}
              {detectedPatterns?.map((d) => (
                <div key={d.pattern_id ?? d.name} className="flex items-center gap-3 px-4 py-2.5">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <p className="truncate text-sm">{d.name ?? d.pattern_id?.replace(/_/g, ' ')}</p>
                      {d.expected ? (
                        <Check className="size-3 text-success" />
                      ) : (
                        <X className="size-3 text-muted-foreground" />
                      )}
                    </div>
                    <p className="font-mono text-[10px] text-muted-foreground">
                      {d.category ?? ''} · {d.nodes ?? 0} nodes
                    </p>
                  </div>
                  <div className="w-16">
                    <Meter value={d.confidence ?? 0} />
                  </div>
                  <span className="w-9 text-right font-mono text-xs tabular-nums">{d.confidence ?? 0}%</span>
                </div>
              ))}
            </div>
          </Panel>

          <Panel>
            <PanelHeader>
              <PanelTitle>
                <GitCompare className="size-4 text-primary" />
                Matching Engine
              </PanelTitle>
              <Badge variant={matchScore >= 80 ? 'success' : 'warning'}>{Math.round(matchScore)}% match</Badge>
            </PanelHeader>
            <PanelBody className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Expected pattern alignment</span>
                <span className="font-mono text-sm tabular-nums">{Math.round(matchScore)}%</span>
              </div>
              <Meter value={matchScore} />
              <div className="grid grid-cols-2 gap-2 pt-1">
                <div className="rounded-md border border-border bg-secondary/40 p-2">
                  <p className="font-mono text-[10px] uppercase text-muted-foreground">matched</p>
                  <p className="font-mono text-lg tabular-nums text-success">{matchedCount}/{totalCount || 1}</p>
                </div>
                <div className="rounded-md border border-border bg-secondary/40 p-2">
                  <p className="font-mono text-[10px] uppercase text-muted-foreground">divergent</p>
                  <p className="font-mono text-lg tabular-nums text-warning">{divergentCount}</p>
                </div>
              </div>
            </PanelBody>
          </Panel>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel className="lg:col-span-2">
          <PanelHeader>
            <PanelTitle>
              <TriangleAlert className="size-4 text-warning" />
              Gap Signals
            </PanelTitle>
            <span className="font-mono text-[10px] text-muted-foreground">
              {gapData?.gap_signals?.length ?? 0} signals
            </span>
          </PanelHeader>
          <div className="divide-y divide-border">
            {!gapData?.gap_signals?.length && (
              <div className="px-4 py-6 text-center text-sm text-muted-foreground">
                No gap signals yet.
              </div>
            )}
            {gapData?.gap_signals?.map((g) => {
              const severity = g.gap_strength >= 0.7 ? 'high' : g.gap_strength >= 0.4 ? 'medium' : 'low'
              const meta = SEVERITY[severity]
              return (
                <div key={g.pattern_id} className="flex items-center gap-3 px-4 py-2.5">
                  <Badge variant={meta.variant}>{meta.label}</Badge>
                  <p className="flex-1 truncate text-sm">{g.pattern_id.replace(/_/g, ' ')}</p>
                  <div className="w-24">
                    <Meter value={g.gap_strength * 100} />
                  </div>
                  <span className="w-9 text-right font-mono text-xs tabular-nums text-muted-foreground">
                    {Math.round(g.gap_strength * 100)}
                  </span>
                </div>
              )
            })}
          </div>
        </Panel>

        <Panel>
          <PanelHeader>
            <PanelTitle>
              <Zap className="size-4 text-primary" />
              Elo Update Preview
            </PanelTitle>
          </PanelHeader>
          <PanelBody className="flex flex-col gap-3">
            {!result && (
              <p className="text-xs text-muted-foreground">
                Run analysis to see how your Elo would change based on detected patterns.
              </p>
            )}
            {result && detectedPatterns?.[0] && (
              <>
                <div className="flex items-baseline justify-between">
                  <div>
                    <p className="font-mono text-[10px] uppercase text-muted-foreground">
                      {detectedPatterns[0].name ?? detectedPatterns[0].pattern_id?.replace(/_/g, ' ')}
                    </p>
                    <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">
                      {eloData?.pattern_elo?.[detectedPatterns[0].pattern_id ?? ''] ?? '-'}
                    </p>
                  </div>
                </div>
                <p className="text-xs leading-relaxed text-muted-foreground">
                  AST analysis complete. The matching engine compared detected patterns against expected
                  patterns for this problem. Check gap signals for optimization opportunities.
                </p>
              </>
            )}
          </PanelBody>
        </Panel>
      </div>
    </div>
  )
}
