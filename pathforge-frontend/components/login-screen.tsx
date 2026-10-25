'use client'

import { ArrowRight, Braces, Compass, Layers2 } from 'lucide-react'
import { signInWithGoogle } from '@/auth/authService'
import { BrandMark } from '@/components/brand-mark'
import { ProductTour } from '@/components/product-tour'
import Link from 'next/link'

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

export function LoginScreen() {
  return (
    <div className="mx-auto flex min-h-svh max-w-[1440px] flex-col px-6 py-8 sm:px-12">
      <header className="flex items-center justify-between"><div className="flex items-center gap-3"><BrandMark className="size-11" /><span className="text-lg font-bold tracking-tight">PathForge</span></div><span className="hidden text-xs text-muted-foreground sm:block">A workspace for deliberate practice</span></header>
      <main className="grid flex-1 items-center gap-10 py-12 lg:grid-cols-[0.95fr_1.05fr] lg:gap-16">
        <div className="max-w-xl">
          <p className="eyebrow mb-5 text-mint"><span className="h-px w-7 bg-mint" />See the structure. Find your next step.</p>
          <h1 className="text-4xl font-semibold leading-[1.12] tracking-[-0.05em] sm:text-5xl lg:text-6xl">See the approach <span>behind your code.</span></h1>
          <p className="mt-6 max-w-lg text-base leading-relaxed text-muted-foreground sm:text-lg">Bring a Python solution. Explore the patterns in its structure, compare available approaches, and choose what to practise next.</p>
          <button type="button" onClick={() => signInWithGoogle()} className="action-primary mt-7 gap-3 px-5"><GoogleMark className="size-4" />Sign in with Google<ArrowRight className="ml-2 size-4" /></button>
          <p className="mt-3 text-sm text-muted-foreground">Keep your practice record in one place.</p>
          <div className="mt-9 flex flex-wrap gap-5 border-t border-border pt-5 text-xs text-muted-foreground"><span className="inline-flex items-center gap-2"><Braces className="size-4 text-mint" />Code evidence</span><span className="inline-flex items-center gap-2"><Layers2 className="size-4 text-sky" />Approach comparison</span><span className="inline-flex items-center gap-2"><Compass className="size-4 text-amber" />Next practice</span></div>
        </div>
        <ProductTour />
      </main>
      <footer className="flex flex-wrap justify-between gap-3 border-t border-border pt-5 text-xs text-muted-foreground"><span>PathForge · A clearer view of your practice.</span><Link href="/companion" className="text-link">Get the Firefox companion <ArrowRight className="size-3" /></Link><span>Inspects patterns; does not execute code or prove correctness.</span></footer>
    </div>
  )
}
