'use client'

import { Award, Flame, Target } from 'lucide-react'
import { Panel, PanelBody, PanelHeader, PanelTitle } from '@/components/ui/panel'
import { Badge } from '@/components/ui/badge'
import { StatTile } from '@/components/ui/stat'
import { useAuth } from '@/auth/AuthProvider'
import { useEloData } from '@/hooks/useApi'
import { getInitials } from '@/lib/utils'

export function ProfileView() {
  const { profile: authProfile, user, signOut } = useAuth()
  const { data: eloData } = useEloData(authProfile?.user_id ?? 0)

  const displayName =
    authProfile?.display_name || user?.user_metadata?.full_name || 'User'
  const email =
    authProfile?.email || user?.email || 'No email'
  const initials = getInitials(displayName)
  const overallElo = eloData?.summary?.average_elo ?? 0
  const patternsTracked = eloData?.pattern_elo ? Object.keys(eloData.pattern_elo).length : 0

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Profile &amp; Settings</h1>
        <p className="text-sm text-muted-foreground">
          Account details, authentication, and learning engine preferences.
        </p>
      </div>

      <Panel>
        <PanelBody className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <div className="flex size-14 items-center justify-center rounded-lg bg-primary/15 font-mono text-xl font-semibold text-primary">
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base font-semibold">{displayName}</h2>
              {overallElo > 0 && (
                <Badge variant="accent">Elo {Math.round(overallElo)}</Badge>
              )}
            </div>
            <p className="font-mono text-xs text-muted-foreground">{email}</p>
          </div>
          <button
            onClick={signOut}
            className="rounded-md border border-border bg-secondary px-3 py-1.5 text-sm font-medium hover:bg-accent"
          >
            Sign out
          </button>
        </PanelBody>
      </Panel>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile
          label="Overall Elo"
          value={Math.round(overallElo)}
          icon={Award}
          accent
        />
        <StatTile
          label="Patterns Tracked"
          value={patternsTracked}
          icon={Target}
        />
        <StatTile
          label="Streak"
          value={`${authProfile?.current_streak ?? 0}d`}
          icon={Flame}
        />
        <StatTile
          label="Sign In"
          value={user?.app_metadata?.provider ?? 'google'}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel>
          <PanelHeader>
            <PanelTitle>Authentication</PanelTitle>
          </PanelHeader>
          <div className="divide-y divide-border">
            <div className="flex items-center justify-between px-4 py-3">
              <div>
                <p className="text-sm">Provider</p>
                <p className="font-mono text-xs text-muted-foreground">
                  {user?.app_metadata?.provider ?? 'Google'}
                </p>
              </div>
              <Badge variant="success">connected</Badge>
            </div>
            <div className="flex items-center justify-between px-4 py-3">
              <div>
                <p className="text-sm">Email</p>
                <p className="font-mono text-xs text-muted-foreground">{email}</p>
              </div>
              <Badge variant="success">verified</Badge>
            </div>
          </div>
        </Panel>

        <Panel>
          <PanelHeader>
            <PanelTitle>Pattern Profiles</PanelTitle>
          </PanelHeader>
          <div className="divide-y divide-border">
            {!patternsTracked && (
              <div className="px-4 py-6 text-center text-sm text-muted-foreground">
                No pattern profiles yet. Submit code to initialize.
              </div>
            )}
            {eloData?.pattern_elo && Object.entries(eloData.pattern_elo)
              .sort(([, a], [, b]) => b - a)
              .map(([topic, elo]) => (
                <div
                  key={topic}
                  className="flex items-center justify-between px-4 py-2.5"
                >
                  <span className="text-sm">{topic.replace(/_/g, ' ')}</span>
                  <span className="font-mono text-sm tabular-nums">
                    {Math.round(elo)}
                  </span>
                </div>
              ))}
          </div>
        </Panel>
      </div>
    </div>
  )
}
