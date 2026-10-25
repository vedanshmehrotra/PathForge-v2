import type { Metadata } from 'next'
import { CompanionConnect } from '@/components/companion-connect'

export const metadata: Metadata = {
  title: 'Connect your companion | PathForge',
  robots: { index: false, follow: false },
}

export default function ConnectPage() {
  return <CompanionConnect />
}
