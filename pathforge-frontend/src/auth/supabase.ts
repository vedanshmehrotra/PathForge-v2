import { createClient } from '@supabase/supabase-js'

let _client: ReturnType<typeof createClient> | null = null

function getSupabaseClient() {
  if (_client) return _client

  const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
  const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    if (typeof window !== 'undefined') {
      console.warn(
        'Supabase env vars not set. Configure NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in .env.local',
      )
    }
    return null
  }

  _client = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
      flowType: 'pkce',
    },
  })

  return _client
}

export const supabase = new Proxy(
  {},
  {
    get(_, prop) {
      const client = getSupabaseClient()
      if (!client) {
        if (prop === 'auth') {
          return {
            getSession: () => Promise.resolve({ data: { session: null }, error: null }),
            onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
            signInWithOAuth: async () => ({ data: null, error: new Error('Supabase not configured') }),
            signOut: async () => {},
          }
        }
        return () => Promise.resolve(null)
      }
      return (client as any)[prop]
    },
  },
) as ReturnType<typeof createClient>
