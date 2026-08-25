'use client'

import { useState } from 'react'
import { FlaskConical, ChevronDown, ChevronRight } from 'lucide-react'
import { Panel, PanelBody, PanelHeader, PanelTitle } from '@/components/ui/panel'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { mapShadowToDisplay, type ShadowDisplayData } from '@/src/services/shadow-mapper'
import type { ShadowAnalysisResult } from '@/src/types/api'

// ============================================================
// Status styling
// ============================================================

const STATUS_CONFIG = {
  likely_match: {
    badgeVariant: 'success' as const,
    icon: '✓',
  },
  not_enough_evidence: {
    badgeVariant: 'warning' as const,
    icon: '—',
  },
  possible_mismatch: {
    badgeVariant: 'danger' as const,
    icon: '?',
  },
} as const

// ============================================================
// Developer Details (collapsed by default)
// ============================================================

function DeveloperDetails({ data }: { data: ShadowDisplayData['developerDetails'] }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="mt-3 rounded-md border border-border bg-muted/20">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-[11px] font-medium text-muted-foreground hover:text-foreground"
      >
        {open ? (
          <ChevronDown className="size-3" />
        ) : (
          <ChevronRight className="size-3" />
        )}
        Developer details
      </button>
      {open && (
        <div className="space-y-2 border-t border-border px-3 py-2.5 font-mono text-[10px] text-muted-foreground">
          <Row label="Outcome" value={data.outcome} />
          <Row label="Authority" value={data.authorityTier || '—'} />
          <Row label="Facts" value={String(data.factCount)} />
          <Row label="Latency" value={`${data.elapsedMs.toFixed(1)}ms`} />
          <Row label="Extractor" value={data.extractorVersion || '—'} />
          {data.strategies.length > 0 && (
            <div>
              <span className="uppercase">Strategies</span>
              {data.strategies.map((s) => (
                <div key={s.id} className="ml-2">
                  {s.name}: {(s.confidence * 100).toFixed(0)}%
                </div>
              ))}
            </div>
          )}
          {data.techniques.length > 0 && (
            <div>
              <span className="uppercase">Techniques</span>
              {data.techniques.map((t) => (
                <div key={t.id} className="ml-2">
                  {t.name}: {(t.confidence * 100).toFixed(0)}%
                </div>
              ))}
            </div>
          )}
          {data.reasoning.length > 0 && (
            <div>
              <span className="uppercase">Reasoning</span>
              {data.reasoning.slice(0, 5).map((r, i) => (
                <div key={i} className="ml-2 break-words">{r}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="uppercase">{label}</span>
      <span className="text-foreground">{value}</span>
    </div>
  )
}

// ============================================================
// Main Experimental Panel
// ============================================================

interface ExperimentalPanelProps {
  shadowAnalysis: ShadowAnalysisResult | null | undefined
}

/**
 * Experimental Analysis panel — a simple, non-technical summary of the
 * shadow analysis result. Visually secondary and clearly labeled as experimental.
 *
 * Hidden when shadow_analysis is absent or invalid.
 */
export function ExperimentalPanel({ shadowAnalysis }: ExperimentalPanelProps) {
  const data = mapShadowToDisplay(shadowAnalysis)

  // Hidden by default — no shadow data means no panel
  if (!data.visible) return null

  const config = STATUS_CONFIG[data.status]

  return (
    <Panel className="border-dashed border-accent/30 bg-accent/5">
      <PanelHeader>
        <PanelTitle>
          <FlaskConical className="size-4 text-accent" />
          Experimental Analysis
        </PanelTitle>
        <Badge variant="outline" className="text-accent">
          Beta
        </Badge>
      </PanelHeader>
      <PanelBody className="flex flex-col gap-3">
        {/* Status line */}
        <div className="flex items-center gap-2">
          <Badge variant={config.badgeVariant}>
            {config.icon} {data.statusLabel}
          </Badge>
          {data.confidence !== '—' && (
            <span className="text-xs text-muted-foreground">
              Confidence: {data.confidence}
            </span>
          )}
        </div>

        {/* Approach */}
        <div>
          <p className="mb-1 font-mono text-[10px] uppercase text-muted-foreground">
            {data.approaches[0] === 'Approach unclear'
              ? 'Approach'
              : 'Likely approach'}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {data.approaches.map((name) => (
              <Badge key={name} variant="outline" className="text-xs">
                {name}
              </Badge>
            ))}
          </div>
        </div>

        {/* Explanation */}
        <div>
          <p className="mb-1 font-mono text-[10px] uppercase text-muted-foreground">
            Why
          </p>
          <p className="text-xs text-foreground/80">{data.explanation}</p>
        </div>

        {/* Developer details (collapsed) */}
        <DeveloperDetails data={data.developerDetails} />
      </PanelBody>
    </Panel>
  )
}
