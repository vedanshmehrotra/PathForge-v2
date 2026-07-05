'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Activity,
  GitBranch,
  LayoutDashboard,
  LogOut,
  ScanLine,
  Settings,
  Target,
  TrendingUp,
} from 'lucide-react'
import { cn, getInitials } from '@/lib/utils'
import { useAuth } from '@/auth/AuthProvider'

const NAV = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard, section: 'Overview' },
  { href: '/analysis', label: 'Code Analysis', icon: ScanLine, section: 'Overview' },
  { href: '/progress', label: 'Learning Progress', icon: TrendingUp, section: 'Insights' },
  { href: '/recommendations', label: 'Recommendations', icon: Target, section: 'Insights' },
  { href: '/profile', label: 'Profile & Settings', icon: Settings, section: 'Account' },
]

const SECTIONS = ['Overview', 'Insights', 'Account'] as const

const TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/analysis': 'Code Analysis',
  '/progress': 'Learning Progress',
  '/recommendations': 'Recommendations',
  '/profile': 'Profile & Settings',
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const title = TITLES[pathname] ?? 'PathForge'
  const { user, profile, loading, signInWithGoogle, signOut } = useAuth()
  console.log("[AppShell]", { pathname, loading, authenticated: !!user })

  const displayName = profile?.display_name || user?.user_metadata?.full_name || ''
  const initials = displayName ? getInitials(displayName) : '??'
  const email = profile?.email || user?.email || ''

  if (loading) {
    return (
      <div className="flex min-h-svh items-center justify-center">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Activity className="size-4 animate-pulse" />
          Loading...
        </div>
      </div>
    )
  }

  if (!user) {
    if (pathname.startsWith('/auth/callback')) {
      return <>{children}</>
    }

    return (
      <div className="flex min-h-svh flex-col items-center justify-center gap-6 px-4">
        <div className="flex items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-md bg-primary/15 text-primary">
            <GitBranch className="size-5" strokeWidth={2.25} />
          </div>
          <div className="flex flex-col leading-none">
            <span className="text-lg font-semibold tracking-tight">PathForge</span>
            <span className="font-mono text-xs text-muted-foreground">skill intelligence</span>
          </div>
        </div>
        <p className="text-center text-sm text-muted-foreground">
          Sign in to track your coding skill development with AST analysis, Elo scoring, and
          personalized recommendations.
        </p>
        <button
          onClick={signInWithGoogle}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          <svg className="size-4" viewBox="0 0 24 24" fill="none">
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
          Sign in with Google
        </button>
      </div>
    )
  }

  return (
    <div className="flex min-h-svh w-full">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r border-border bg-sidebar md:flex">
        <div className="flex h-14 items-center gap-2 border-b border-border px-4">
          <div className="flex size-7 items-center justify-center rounded-md bg-primary/15 text-primary">
            <GitBranch className="size-4" strokeWidth={2.25} />
          </div>
          <div className="flex flex-col leading-none">
            <span className="text-sm font-semibold tracking-tight">PathForge</span>
            <span className="font-mono text-[10px] text-muted-foreground">skill intelligence</span>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4">
          {SECTIONS.map((section) => (
            <div key={section} className="mb-5">
              <p className="px-2 pb-1.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground/70">
                {section}
              </p>
              <ul className="flex flex-col gap-0.5">
                {NAV.filter((n) => n.section === section).map((item) => {
                  const active = pathname === item.href
                  const Icon = item.icon
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        className={cn(
                          'group flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors',
                          active
                            ? 'bg-sidebar-accent text-foreground'
                            : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground',
                        )}
                      >
                        <Icon
                          className={cn('size-4 shrink-0', active ? 'text-primary' : 'text-muted-foreground')}
                          strokeWidth={2}
                        />
                        <span className="truncate">{item.label}</span>
                      </Link>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </nav>

        <div className="border-t border-border p-3">
          <div className="flex items-center gap-2.5 rounded-md px-2 py-1.5">
            <div className="flex size-7 items-center justify-center rounded-full bg-secondary font-mono text-xs font-medium text-foreground">
              {initials}
            </div>
            <div className="flex min-w-0 flex-1 flex-col leading-tight">
              <span className="truncate text-sm font-medium">{displayName || email}</span>
              {profile?.email && (
                <span className="truncate font-mono text-[10px] text-muted-foreground">
                  {profile.email}
                </span>
              )}
            </div>
            <button
              onClick={signOut}
              aria-label="Sign out"
              className="shrink-0 text-muted-foreground hover:text-foreground"
            >
              <LogOut className="size-4" />
            </button>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col md:pl-60">
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between gap-4 border-b border-border bg-background/80 px-4 backdrop-blur md:px-6">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-mono text-xs text-muted-foreground">pathforge /</span>
            <span className="font-medium">{title}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 rounded-md border border-success/30 bg-success/10 px-2 py-1.5 font-mono text-[11px] text-success">
              <Activity className="size-3" />
              engine live
            </div>
          </div>
        </header>

        <main className="flex-1 px-4 py-5 md:px-6 md:py-6">{children}</main>
      </div>
    </div>
  )
}
