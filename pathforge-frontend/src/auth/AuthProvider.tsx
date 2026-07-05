'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
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
  signInWithGoogle: () => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  session: null,
  profile: null,
  loading: true,
  signInWithGoogle: async () => {},
  signOut: async () => {},
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  console.log("AUTH_DEBUG_BUILD_V8");
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)

  const syncToken = useCallback((accessToken: string | null) => {
    setAccessToken(accessToken)
  }, [])

  const loadProfile = useCallback(async () => {
    try {
      const p = await fetchMe()
      setProfile(p)
    } catch {
      setProfile(null)
    }
  }, [])

  useEffect(() => {
    console.log("[AuthProvider] Before getSession()")
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      console.log("[AuthProvider] Session:", s ? "exists" : "null")
      setSession(s)
      setUser(s?.user ?? null)
      syncToken(s?.access_token ?? null)
      if (s?.access_token) {
        loadProfile()
      }
      setLoading(false)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, s) => {
      console.log("[AuthProvider] Event:", _event, "Session:", s ? "exists" : "null")
      setSession(s)
      setUser(s?.user ?? null)
      syncToken(s?.access_token ?? null)
      if (s?.access_token) {
        loadProfile()
      } else {
        setProfile(null)
      }
    })

    return () => subscription.unsubscribe()
  }, [syncToken, loadProfile])

  const signInWithGoogle = useCallback(async () => {
    const redirectTo =
      process.env.NEXT_PUBLIC_REDIRECT_URL ||
      `${window.location.origin}/auth/callback`
    console.log("[AuthProvider] redirectTo:", redirectTo)
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo },
    })
  }, [])

  const signOut = useCallback(async () => {
    await supabase.auth.signOut()
    setUser(null)
    setSession(null)
    setProfile(null)
    syncToken(null)
  }, [syncToken])

  return (
    <AuthContext.Provider
      value={{ user, session, profile, loading, signInWithGoogle, signOut }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
