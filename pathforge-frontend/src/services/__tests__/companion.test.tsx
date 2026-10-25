import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import CompanionPage from '../../../app/companion/page'
import { CompanionConnect } from '../../../components/companion-connect'
import { signInWithGoogle } from '../../auth/authService'

const fixture = vi.hoisted(() => ({ signedIn: false, loading: false, oauth: vi.fn() }))
vi.mock('@/auth/AuthProvider', () => ({ useAuth: () => ({ user: fixture.signedIn ? { email: 'sample@example.invalid' } : null, loading: fixture.loading }) }))
vi.mock('../../auth/supabase', () => ({ supabase: { auth: { signInWithOAuth: fixture.oauth } } }))
beforeEach(() => {
  fixture.signedIn = false; fixture.loading = false
  fixture.oauth.mockResolvedValue({ error: null })
  vi.stubGlobal('window', { location: { origin: 'https://example.invalid', href: 'https://example.invalid/companion' } })
  vi.stubGlobal('sessionStorage', { setItem: vi.fn() })
})
afterEach(() => vi.unstubAllGlobals())

describe('public companion and sign-in handoff', () => {
  it('renders product facts, official install, privacy and limitations in server HTML', () => {
    const html = renderToStaticMarkup(createElement(CompanionPage))
    expect(html).toContain('Find the pattern')
    expect(html).toContain('https://addons.mozilla.org/en-US/firefox/addon/pathforge-companion/')
    expect(html).toContain('application/ld+json')
    expect(html).toContain('Failed submissions do not cost XP')
    expect(html).toContain('illustrative sample data')
    expect(html).not.toMatch(/aggregateRating|reviewCount|guaranteed mastery/)
  })

  it('takes a signed-in extension user back to connection instructions', () => {
    fixture.signedIn = true
    const html = renderToStaticMarkup(createElement(CompanionConnect))
    expect(html).toContain('sample@example.invalid')
    expect(html).toContain('Connect account')
    expect(html).not.toContain('analysis workbench')
  })

  it('offers sign-in when disconnected without pretending the extension is connected', () => {
    const html = renderToStaticMarkup(createElement(CompanionConnect))
    expect(html).toContain('Sign in with Google')
    expect(html).not.toContain('Already connected?')
  })

  it('keeps only the allowlisted connection destination through normal OAuth', async () => {
    await signInWithGoogle('/companion/connect')
    expect(sessionStorage.setItem).toHaveBeenLastCalledWith('pathforgeAuthReturn', '/companion/connect')
    await signInWithGoogle('https://untrusted.invalid')
    expect(sessionStorage.setItem).toHaveBeenLastCalledWith('pathforgeAuthReturn', '/')
    expect(fixture.oauth).toHaveBeenCalledWith(expect.objectContaining({ provider: 'google' }))
  })
})
