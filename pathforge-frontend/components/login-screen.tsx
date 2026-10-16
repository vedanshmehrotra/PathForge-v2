'use client'

import { GitBranch } from 'lucide-react'
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
        <span className="font-mono text-[10px] text-muted-foreground">practice workspace</span>
      </div>
    </div>
  )
}

const EXAMPLE = [
  'window = sum(values[:width])',
  'for index in range(width, len(values)):',
  '    window += values[index]',
  '    window -= values[index - width]',
].join('\n')

export function LoginScreen() {
  return (
    <div className="mx-auto flex min-h-svh max-w-[1440px] flex-col px-6 py-8 sm:px-12">
      <header><Brand /></header>
      <main className="grid flex-1 items-center gap-12 py-14 lg:grid-cols-[1.15fr_1fr] lg:gap-20">
        <div className="max-w-xl">
          <h1 className="text-4xl font-semibold leading-tight tracking-tight sm:text-5xl lg:text-6xl">See the approach behind your code.</h1>
          <p className="mt-6 max-w-lg text-lg leading-relaxed text-muted-foreground">Bring a Python solution. Explore the patterns in its structure, compare available approaches, and choose what to practise next.</p>
          <button type="button" onClick={signInWithGoogle} className="action-primary mt-8 gap-3 px-6"><GoogleMark className="size-4" />Sign in with Google</button>
          <p className="mt-3 text-sm text-muted-foreground">Keep your practice record in one place.</p>
        </div>
        <section className="min-w-0 border-y border-border py-6 lg:border-y-0 lg:border-l lg:py-2 lg:pl-10" aria-labelledby="example-heading">
          <p className="workspace-kicker">An example of what to look for</p>
          <h2 id="example-heading" className="mt-3 text-xl font-medium">The window moves. Its width stays fixed.</h2>
          <pre className="my-6 overflow-x-auto rounded-md bg-card p-4 font-mono text-xs leading-loose sm:text-sm"><code>{EXAMPLE}</code></pre>
          <p className="text-base leading-relaxed text-muted-foreground">An incoming element is added and the outgoing element is removed from the same running total. That relationship is more useful than a variable name alone.</p>
          <p className="mt-5 text-sm text-muted-foreground">Illustrative Python snippet. PathForge inspects patterns; it does not execute code or prove that a solution is correct.</p>
        </section>
      </main>
      <footer className="border-t border-border pt-5 text-xs text-muted-foreground">PathForge · A clearer view of your practice.</footer>
    </div>
  )
}