'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/auth/supabase'

export default function AuthCallbackPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN' && session) {
        router.push('/')
      }
    })

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        router.push('/')
      } else {
        setError('Authentication failed. Please try again.')
      }
    })
  }, [router])

  if (error) {
    return (
      <div className="flex min-h-svh items-center justify-center">
        <div className="text-center">
          <p className="text-destructive">{error}</p>
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
