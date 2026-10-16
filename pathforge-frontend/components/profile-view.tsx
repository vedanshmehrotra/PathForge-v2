'use client'

import Link from 'next/link'
import { useAuth } from '@/auth/AuthProvider'
import { getInitials } from '@/lib/utils'

export function ProfileView() {
  const { profile, user, signOut } = useAuth()
  const displayName = profile?.display_name || user?.user_metadata?.full_name || 'Your account'
  const email = profile?.email || user?.email

  return (
    <div className="workspace-page max-w-3xl">
      <header className="page-intro">
        <p className="workspace-kicker">PathForge account</p>
        <h1 className="page-heading">Account</h1>
        <p className="page-description">Your sign-in details and account information.</p>
      </header>
      <section className="border-y border-border py-8" aria-labelledby="account-name">
        <div className="flex items-center gap-4">
          <div className="flex size-12 shrink-0 items-center justify-center rounded-md bg-secondary text-lg font-medium">{getInitials(displayName)}</div>
          <div className="min-w-0"><h2 id="account-name" className="text-xl font-medium">{displayName}</h2><p className="mt-1 break-all text-sm text-muted-foreground">{email || 'Email not available'}</p></div>
        </div>
        <dl className="mt-8 divide-y divide-border text-sm">
          <div className="flex flex-wrap justify-between gap-3 py-4"><dt className="text-muted-foreground">Sign-in provider</dt><dd className="capitalize">{user?.app_metadata?.provider || 'Not available'}</dd></div>
          <div className="flex flex-wrap justify-between gap-3 py-4"><dt className="text-muted-foreground">Email status</dt><dd>{user?.email_confirmed_at ? 'Email verified' : 'Verification not confirmed'}</dd></div>
        </dl>
        <button type="button" onClick={signOut} className="action-secondary mt-6">Sign out</button>
      </section>
      <section>
        <h2 className="section-title">Looking for your practice record?</h2>
        <p className="mt-3 text-base text-muted-foreground">Your recorded patterns and their details live in Learning Progress.</p>
        <Link href="/progress" className="text-link mt-4">Open your practice notebook</Link>
      </section>
    </div>
  )
}
