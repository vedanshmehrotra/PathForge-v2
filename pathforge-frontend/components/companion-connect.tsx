'use client'

import Link from 'next/link'
import { useState } from 'react'
import { ArrowRight, Check } from 'lucide-react'
import { useAuth } from '@/auth/AuthProvider'
import { signInWithGoogle } from '@/auth/authService'
import { BrandMark } from '@/components/brand-mark'

export function CompanionConnect() {
  const { user, loading } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [signingIn, setSigningIn] = useState(false)
  const signIn = async () => {
    setError(null); setSigningIn(true)
    try { setError(await signInWithGoogle('/companion/connect')) }
    catch { setError('Sign-in could not start. Please try again.') }
    finally { setSigningIn(false) }
  }
  return (
    <main className="mx-auto flex min-h-svh max-w-xl flex-col justify-center px-6 py-12">
      <Link href="/companion" aria-label="About PathForge Companion"><BrandMark className="mb-8 size-12" /></Link>
      {loading ? <p role="status">Checking your PathForge sign-in…</p> : user ? <>
        <p className="eyebrow text-mint"><Check className="size-4" />Signed in</p>
        <h1 className="page-heading mt-4">Back to LeetCode. One last step.</h1>
        <p className="mt-5 text-muted-foreground">You’re signed in as <span className="break-all text-foreground">{user.email}</span>.</p>
        <ol className="mt-7 list-decimal space-y-4 pl-5 text-sm leading-relaxed">
          <li>Return to your LeetCode tab and open the PathForge sidebar.</li>
          <li>Choose <strong>Connect account</strong>. Your solution will appear automatically.</li>
          <li>Submit on LeetCode for a correctness check. Drafts and Run/Test never change XP.</li>
        </ol>
        <p className="mt-6 text-sm text-muted-foreground">Already connected? You can close this page and keep practising.</p>
        <a href="https://leetcode.com/problems/two-sum/" className="action-primary mt-7 self-start">Open Two Sum <ArrowRight className="size-4" /></a>
      </> : <>
        <p className="eyebrow text-mint">PathForge Companion · Step 1 of 2</p>
        <h1 className="page-heading mt-4">Connect your practice.</h1>
        <p className="mt-5 leading-relaxed text-muted-foreground">Sign in with Google, then return to the sidebar and choose Connect account. Use this same browser window.</p>
        <button type="button" onClick={signIn} disabled={signingIn} className="action-primary mt-7 self-start disabled:opacity-50">{signingIn ? 'Opening Google…' : 'Sign in with Google'} <ArrowRight className="size-4" /></button>
        {error && <p role="alert" className="mt-4 text-sm text-destructive">{error}</p>}
      </>}
      <p className="mt-10 border-t border-border pt-5 text-xs leading-relaxed text-muted-foreground">The connected extension sends your LeetCode solution and problem to PathForge for analysis and progress tracking. It does not submit code to LeetCode for you.</p>
    </main>
  )
}
