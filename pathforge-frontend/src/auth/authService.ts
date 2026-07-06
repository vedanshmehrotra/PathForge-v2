import { supabase } from './supabase'

export async function signInWithGoogle() {
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
}
