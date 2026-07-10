'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/auth/supabase'

export default function AuthCallbackPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    console.log("[callback] mounted")

    async function handleCallback() {
      const code = new URLSearchParams(window.location.search).get("code")

      console.log("[callback] code:", code)

      if (!code) {
        console.log("[callback] no code found")

        const { data: { session } } = await supabase.auth.getSession()

        console.log("[callback] existing session:", !!session)

        if (session) {
          router.replace("/")
          return
        }

        setError("No authorization code received. Please try signing in again.")
        return
      }

      console.log("[callback] before exchange")

      const { data, error: exchangeError } =
        await supabase.auth.exchangeCodeForSession(code)

      console.log("[callback] after exchange", {
        session: !!data?.session,
        error: exchangeError?.name,
      })

      if (exchangeError) {
        console.error("[OAuth Exchange]", exchangeError)

        if (exchangeError.name === "AuthPKCECodeVerifierMissingError") {
          const { data: { session } } = await supabase.auth.getSession()

          console.log("[callback] fallback session:", !!session)

          if (session) {
            router.replace("/")
            return
          }
        }

        setError(exchangeError.message)
        return
      }

      if (data?.session) {
        console.log("[callback] redirecting")
        router.replace("/")
      } else {
        setError("Authentication completed but no session was returned.")
      }
    }

    handleCallback()
  }, [router])

  if (error) {
    return (
      <div className="flex min-h-svh items-center justify-center">
        <div className="text-center">
          <p className="text-destructive mb-2 text-sm">{error}</p>
          <button
            onClick={() => router.push('/')}
            className="mt-4 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground"
          >
            Go Home
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-svh items-center justify-center">
      <p className="text-sm text-muted-foreground">Completing sign in...</p>
    </div>
  )
}
