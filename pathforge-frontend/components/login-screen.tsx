'use client'

import { useEffect, useState } from 'react'
import { GitBranch } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { signInWithGoogle } from '@/auth/authService'

function GoogleMark({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
        fill="#4285F4"
      />
      <path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <path
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        fill="#EA4335"
      />
    </svg>
  )
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={cn(
          'flex items-center justify-center rounded-md bg-primary/15 text-primary',
          compact ? 'size-7' : 'size-8',
        )}
      >
        <GitBranch className={compact ? 'size-4' : 'size-5'} strokeWidth={2.25} />
      </div>
      <div className="flex flex-col leading-none">
        <span className={cn('font-semibold tracking-tight', compact ? 'text-sm' : 'text-base')}>
          PathForge
        </span>
        <span className="font-mono text-[10px] text-muted-foreground">skill intelligence</span>
      </div>
    </div>
  )
}

// The preview is a small, quiet depiction of the actual product so a first-time
// visitor can see what PathForge does. It is illustrative only — never the
// signed-in user's data — and cycles slowly in the background.
const PREVIEW_TABS = ['Dashboard', 'Analysis', 'Progress', 'Practice'] as const

function PreviewDashboard() {
  return (
    <>
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-medium text-foreground">Recent submissions</span>
        <span className="font-mono text-[10px] text-muted-foreground">today</span>
      </div>
      <div className="divide-y divide-border">
        <div className="flex items-center justify-between py-2.5">
          <div className="min-w-0">
            <p className="truncate text-xs text-foreground">Two Sum</p>
            <p className="font-mono text-[10px] text-muted-foreground">hash_map_lookup</p>
          </div>
          <Badge variant="success">confirmed</Badge>
        </div>
        <div className="flex items-center justify-between py-2.5">
          <div className="min-w-0">
            <p className="truncate text-xs text-foreground">Valid Palindrome</p>
            <p className="font-mono text-[10px] text-muted-foreground">two_pointers_same</p>
          </div>
          <Badge variant="warning">unresolved</Badge>
        </div>
      </div>
    </>
  )
}

function PreviewAnalysis() {
  return (
    <>
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-medium text-foreground">Analysis result</span>
        <Badge variant="success">confirmed</Badge>
      </div>
      <div className="rounded-md border border-border bg-secondary/30 p-3">
        <p className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
          approach identified
        </p>
        <p className="mt-1.5 text-sm font-medium text-foreground">Hash Map Lookup</p>
        <p className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground">
          Store previously seen values and look up the complement in constant time.
        </p>
      </div>
    </>
  )
}

function PreviewProgress() {
  return (
    <>
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-medium text-foreground">Skill progress</span>
        <span className="font-mono text-[10px] text-muted-foreground">updated now</span>
      </div>
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-xs text-foreground">Sliding Window</span>
          <span className="font-mono text-xs tabular-nums text-foreground">1244</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
          <div className="h-full rounded-full bg-primary" style={{ width: '62%' }} />
        </div>
        <p className="font-mono text-[10px] text-success">+18 on last confirmed solve</p>
      </div>
      <div className="mt-3 flex items-center gap-2 rounded-md border border-primary/20 bg-primary/5 px-2.5 py-2 text-[11px] text-muted-foreground">
        <span className="text-primary">next</span>
        <span>Practice Sliding Window with a window-shrink problem</span>
      </div>
    </>
  )
}

function PreviewRecommendation() {
  return (
    <>
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-medium text-foreground">Recommended next</span>
        <span className="font-mono text-[10px] text-muted-foreground">queue</span>
      </div>
      <div className="divide-y divide-border">
        <div className="flex items-center justify-between py-2.5">
          <div className="min-w-0">
            <p className="truncate text-xs text-foreground">Flood Fill</p>
            <p className="font-mono text-[10px] text-muted-foreground">bfs_level_order</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="success">Easy</Badge>
            <span className="font-mono text-[10px] text-success">+25</span>
          </div>
        </div>
        <div className="flex items-center justify-between py-2.5">
          <div className="min-w-0">
            <p className="truncate text-xs text-foreground">Number of Good Pairs</p>
            <p className="font-mono text-[10px] text-muted-foreground">hash_map_frequency</p>
          </div>
          <span className="font-mono text-[10px] text-success">+24</span>
        </div>
      </div>
    </>
  )
}

const PREVIEW_PANELS = [
  PreviewDashboard,
  PreviewAnalysis,
  PreviewProgress,
  PreviewRecommendation,
]

function ProductPreview() {
  const [step, setStep] = useState(0)

  useEffect(() => {
    if (typeof window === 'undefined') return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const id = window.setInterval(() => {
      setStep((current) => (current + 1) % PREVIEW_PANELS.length)
    }, 4300)
    return () => window.clearInterval(id)
  }, [])

  return (
    <div className="w-full max-w-md" aria-hidden="true">
      <div className="overflow-hidden rounded-lg border border-border bg-card">
        <div className="flex h-10 items-center justify-between border-b border-border px-3">
          <Brand compact />
          <span className="font-mono text-[10px] text-muted-foreground">workspace</span>
        </div>
        <div className="flex items-center gap-4 border-b border-border px-3 py-2">
          {PREVIEW_TABS.map((tab, i) => (
            <span
              key={tab}
              className={cn(
                'font-mono text-[10px] uppercase tracking-wide transition-colors duration-700',
                i === step ? 'text-foreground' : 'text-muted-foreground/50',
              )}
            >
              {tab}
            </span>
          ))}
        </div>
        <div className="relative min-h-[200px] p-4">
          {PREVIEW_PANELS.map((PanelContent, i) => (
            <div
              key={i}
              className={cn(
                'transition-opacity duration-1000 ease-out',
                i === step ? 'opacity-100' : 'pointer-events-none absolute inset-0 p-4 opacity-0',
              )}
            >
              <PanelContent />
            </div>
          ))}
        </div>
      </div>
      <p className="mt-3 text-center font-mono text-[10px] text-muted-foreground/60">
        a look at the PathForge workspace
      </p>
    </div>
  )
}

export function LoginScreen() {
  return (
    <div className="grid min-h-svh grid-cols-1 lg:grid-cols-[1fr_minmax(380px,44%)]">
      <div className="flex flex-col justify-between gap-10 border-border p-8 sm:p-12 lg:border-r">
        <Brand />

        <div className="w-full max-w-sm self-center lg:mx-auto">
          <p className="font-mono text-[11px] uppercase tracking-wider text-primary">
            developer skill intelligence
          </p>
          <h1 className="mt-4 text-2xl font-semibold tracking-tight">
            Understand the way you solve.
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            PathForge analyzes your solutions, detects the patterns behind them, and tracks how your
            problem-solving develops over time.
          </p>
          <button
            onClick={signInWithGoogle}
            className="mt-7 inline-flex w-full items-center justify-center gap-2.5 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
          >
            <GoogleMark className="size-4" />
            Sign in with Google
          </button>
          <p className="mt-3 text-xs text-muted-foreground">
            Use your Google account to keep your practice history in one place.
          </p>
        </div>

        <p className="font-mono text-[10px] text-muted-foreground/60">
          &copy; 2026 PathForge &middot; built for deliberate practice
        </p>
      </div>

      <div className="hidden items-center justify-center border-border bg-sidebar/40 p-8 lg:flex">
        <ProductPreview />
      </div>
    </div>
  )
}
