'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'
import type { Session, User } from '@supabase/supabase-js'
import { supabase } from './supabase'
import { setAccessToken } from '@/services/api/client'
import type { UserProfile } from '@/types/api'
import { fetchMe } from '@/services/api/auth'

interface AuthContextValue {
  user: User | null
  session: Session | null
  profile: UserProfile | null
  loading: boolean
  profileLoading?: boolean
  profileError?: string | null
  retryProfile?: () => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  session: null,
  profile: null,
  loading: true,
  signOut: async () => {},
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileError, setProfileError] = useState<string | null>(null)
  const profileRequest = useRef(0)
  const currentSession = useRef<Session | null>(null)

  const syncToken = useCallback((accessToken: string | null) => {
    setAccessToken(accessToken)
  }, [])

  const loadProfile = useCallback(async () => {
    if (!currentSession.current) return
    const request = ++profileRequest.current
    setProfileLoading(true)
    setProfileError(null)
    try {
      const p = await fetchMe()
      if (request === profileRequest.current) setProfile(p)
    } catch {
      if (request === profileRequest.current) {
        setProfile(null)
        setProfileError('Your account could not be loaded. Please retry.')
      }
    } finally {
      if (request === profileRequest.current) setProfileLoading(false)
    }
  }, [])

  useEffect(() => {
    let active = true
    let receivedAuthEvent = false
    const applySession = (s: Session | null) => {
      if (!active) return
      if (currentSession.current?.user.id !== s?.user.id) {
        ++profileRequest.current
        setProfile(null)
        setProfileError(null)
      }
      currentSession.current = s
      setSession(s)
      setUser(s?.user ?? null)
      syncToken(s?.access_token ?? null)
      if (s?.access_token) {
        loadProfile()
      } else {
        ++profileRequest.current
        setProfile(null)
        setProfileLoading(false)
        setProfileError(null)
      }
      setLoading(false)
    }
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      if (!receivedAuthEvent) applySession(s)
    }).catch(() => {
      if (active && !receivedAuthEvent) setLoading(false)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, s) => {
      receivedAuthEvent = true
      applySession(s)
    })

    return () => { active = false; ++profileRequest.current; subscription.unsubscribe() }
  }, [syncToken, loadProfile])

  const signOut = useCallback(async () => {
    await supabase.auth.signOut()
    ++profileRequest.current
    currentSession.current = null
    setUser(null)
    setSession(null)
    setProfile(null)
    setProfileLoading(false)
    setProfileError(null)
    syncToken(null)
  }, [syncToken])

  return (
    <AuthContext.Provider
      value={{ user, session, profile, loading, profileLoading, profileError, retryProfile: loadProfile, signOut }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
