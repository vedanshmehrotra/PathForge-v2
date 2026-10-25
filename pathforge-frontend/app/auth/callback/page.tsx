'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/auth/supabase'
import { BrandMark } from '@/components/brand-mark'

export default function AuthCallbackPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function handleCallback() {
      const code = new URLSearchParams(window.location.search).get("code")
      const complete = () => {
        let destination = '/'
        try {
          if (sessionStorage.getItem('pathforgeAuthReturn') === '/companion/connect') destination = '/companion/connect'
          sessionStorage.removeItem('pathforgeAuthReturn')
        } catch { /* Use the normal dashboard when storage is unavailable. */ }
        router.replace(destination)
      }

      if (!code) {
        const { data: { session } } = await supabase.auth.getSession()

        if (session) {
          complete()
          return
        }

        setError("No authorization code received. Please try signing in again.")
        return
      }

      const { data, error: exchangeError } =
        await supabase.auth.exchangeCodeForSession(code)

      if (exchangeError) {
        console.error("[OAuth Exchange]", exchangeError.name)

        if (exchangeError.name === "AuthPKCECodeVerifierMissingError") {
          const { data: { session } } = await supabase.auth.getSession()

          if (session) {
            complete()
            return
          }
        }

        setError(exchangeError.message)
        return
      }

      if (data?.session) {
        complete()
      } else {
        setError("Authentication completed but no session was returned.")
      }
    }

    handleCallback()
  }, [router])

  if (error) {
    return (
      <main className="flex min-h-svh items-center justify-center px-6">
        <div className="flex w-full max-w-md flex-col items-center text-center">
          <BrandMark className="mb-6 size-11" />
          <p role="alert" className="mb-2 text-sm text-destructive">{error}</p>
          <button
            onClick={() => router.push('/')}
            className="action-primary mt-4"
          >
            Go Home
          </button>
        </div>
      </main>
    )
  }

  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-6 px-6">
      <BrandMark className="size-11" />
      <p role="status" className="text-sm text-muted-foreground">Completing sign in...</p>
    </main>
  )
}
