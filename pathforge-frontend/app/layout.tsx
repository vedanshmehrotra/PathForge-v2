import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import { Manrope, Geist_Mono } from 'next/font/google'
import { AppShell } from '@/components/app-shell'
import { AuthProvider } from '@/auth/AuthProvider'
import './globals.css'

const manrope = Manrope({
  subsets: ['latin'],
  variable: '--font-manrope',
})

const geistMono = Geist_Mono({
  subsets: ['latin'],
  variable: '--font-geist-mono',
})

export const metadata: Metadata = {
  metadataBase: new URL('https://path-forge-v2.vercel.app'),
  title: 'PathForge \u2014 Practice workspace',
  description:
    'Explore patterns in Python solutions, compare available approaches, and choose what to practise next.',
  icons: { icon: '/pathforge-mark.svg', shortcut: '/pathforge-mark.svg' },
}

export const viewport: Viewport = {
  colorScheme: 'dark',
  themeColor: '#0b0c0e',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={`dark ${manrope.variable} ${geistMono.variable}`}>
      <body className="bg-background text-foreground font-sans antialiased">
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
