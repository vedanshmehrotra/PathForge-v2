import { supabase } from './supabase'

export async function signInWithGoogle(returnTo = '/') {
  // Only this fixed same-origin destination may survive the OAuth round trip.
  try { sessionStorage.setItem('pathforgeAuthReturn', returnTo === '/companion/connect' ? returnTo : '/') } catch { /* Sign-in still works without browser storage. */ }
  const redirectTo =
    process.env.NEXT_PUBLIC_REDIRECT_URL ||
    `${window.location.origin}/auth/callback`

  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo },
  })

  if (error) {
    console.error('[AuthService] signInWithGoogle failed:', error.message)
  }
  return error?.message ?? null
}
