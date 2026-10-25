import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowRight, Check } from 'lucide-react'
import { BrandMark } from '@/components/brand-mark'
import { ProductTour } from '@/components/product-tour'

const url = 'https://path-forge-v2.vercel.app/companion'
const install = 'https://addons.mozilla.org/en-US/firefox/addon/pathforge-companion/'
const description = 'Understand the patterns in your LeetCode Python solutions, save your practice, and find related problems with PathForge Companion for Firefox.'
export const metadata: Metadata = {
  title: 'PathForge Companion | LeetCode Python Pattern Practice',
  description,
  alternates: { canonical: url },
  openGraph: { title: 'Find the pattern in your own code.', description, url, siteName: 'PathForge', type: 'website', images: [{ url: '/companion/opengraph-image', width: 1200, height: 630 }] },
  twitter: { card: 'summary_large_image', title: 'PathForge Companion', description, images: ['/companion/opengraph-image'] },
}
const questions = [
  ['What does PathForge Companion do?', 'It reads your Python solution from the LeetCode editor, identifies supported code patterns, saves your practice, and suggests related practice from the PathForge problem bank.'],
  ['Who is it for?', 'Python learners who can attempt Easy LeetCode problems and want to understand their approach and choose a useful next step. It is not a replacement for learning Python basics.'],
  ['Which browsers and languages work?', 'The public add-on supports desktop Firefox 142 or later. The repository also includes a separate Chrome side-panel client. Analysis currently supports Python and Python3.'],
  ['Do I need a PathForge account?', 'Yes. Sign in with Google on PathForge in the same browser, then choose Connect account in the extension sidebar. The website and extension use the same account and backend.'],
  ['Will drafts, failed submissions, or refreshing affect XP?', 'Drafts and Run/Test do not change XP. Failed submissions do not cost XP. A corrected accepted submission can qualify the same day. Each problem can affect XP at most once per UTC day; a repeated scan does not earn another reward.'],
  ['Why can accepted code earn no XP?', 'LeetCode acceptance and pattern detection are separate from XP eligibility. XP requires a supported, verified approach comparison. Practice is saved even when the analyzer cannot award XP. Levels reflect the existing pattern rating and can rise or fall; they do not certify mastery.'],
  ['Does it execute my code or prove correctness?', 'No. Correctness comes from a completed LeetCode submission that matches the captured problem, language, and code. A pattern observation alone does not prove a solution is correct.'],
  ['What information is sent?', 'While connected, opening the sidebar, moving to a problem, or rechecking can send your solution and problem identifier to PathForge for analysis and progress tracking. The extension imports your PathForge session access token for authenticated requests. It does not forward LeetCode cookies or passwords.'],
  ['Are related questions guaranteed to use the same algorithm?', 'No. Related suggestions share a catalog topic with the current problem. The sidebar labels general exploration separately and does not treat shared tags as proof of a required algorithm.'],
]

export default function CompanionPage() {
  const data = {
    '@context': 'https://schema.org', '@type': 'SoftwareApplication', name: 'PathForge Companion', url,
    applicationCategory: 'EducationalApplication', operatingSystem: 'Desktop Firefox 142+', description,
    downloadUrl: install, author: { '@type': 'Person', name: 'Vedansh Mehrotra', url: 'https://github.com/vedanshmehrotra' },
    sameAs: [install, 'https://github.com/vedanshmehrotra/PathForge-v2'],
  }
  return (
    <div className="mx-auto max-w-6xl px-6 py-7 sm:px-10">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, '\\u003c') }} />
      <header className="flex flex-wrap items-center justify-between gap-5 border-b border-border pb-6">
        <Link href="/companion" className="flex items-center gap-3"><BrandMark className="size-10" /><span className="font-semibold">PathForge <span className="text-muted-foreground">Companion</span></span></Link>
        <nav aria-label="Companion navigation" className="flex gap-5 text-sm"><a href="#how-it-works" className="text-muted-foreground hover:text-foreground">How it works</a><Link href="/" className="text-muted-foreground hover:text-foreground">Open website</Link></nav>
      </header>
      <main>
        <section className="grid items-center gap-12 py-14 lg:grid-cols-2 lg:py-20">
          <div>
            <p className="eyebrow text-mint">LeetCode Python practice · Firefox sidebar</p>
            <h1 className="mt-5 text-4xl font-semibold leading-[1.12] tracking-[-0.05em] sm:text-5xl">Find the pattern<br />in your own code.</h1>
            <p className="mt-6 max-w-lg text-lg leading-relaxed text-muted-foreground">Finish a solution. Understand the approach you used. Choose a related problem to practise next.</p>
            <a href={install} className="action-primary mt-7">Get it for Firefox <ArrowRight className="size-4" /></a>
            <p className="mt-3 text-xs text-muted-foreground">Python / Python3 · Firefox 142+ · PathForge account required</p>
            <p className="mt-6 text-sm text-muted-foreground">Already installed? <Link href="/companion/connect" className="text-link">Connect your account <ArrowRight className="size-3" /></Link></p>
            <ul className="mt-8 space-y-3 border-t border-border pt-6 text-sm">{['Code read directly from the LeetCode editor', 'Pattern explanations in plain language', 'Practice saved to your existing PathForge account'].map(item => <li key={item} className="flex gap-3"><Check className="size-4 shrink-0 text-mint" />{item}</li>)}</ul>
          </div>
          <ProductTour companion />
        </section>
        <section id="how-it-works" className="border-y border-border py-10">
          <h2 className="text-2xl font-semibold tracking-tight">Your next session, in three steps.</h2>
          <ol className="mt-7 grid gap-8 md:grid-cols-3">{[
            ['Connect once', 'Install the add-on, sign in on PathForge in the same browser, then connect in the sidebar.'],
            ['Write and submit', 'Open a Python problem on LeetCode. The companion reads your solution; a matching completed submission supplies its verdict.'],
            ['Understand and continue', 'Read a pattern explanation, check whether XP changed, and open a related question when you are ready.'],
          ].map(([title, text], index) => <li key={title}><span className="font-mono text-xs text-mint">0{index + 1}</span><h3 className="mt-3 font-semibold">{title}</h3><p className="mt-2 text-sm leading-relaxed text-muted-foreground">{text}</p></li>)}</ol>
        </section>
        <section className="py-10" aria-labelledby="questions-heading">
          <h2 id="questions-heading" className="mb-6 text-2xl font-semibold tracking-tight">Before you start</h2>
          {questions.map(([question, answer]) => <details key={question} className="border-b border-border py-4"><summary className="cursor-pointer text-sm font-medium">{question}</summary><p className="mt-3 max-w-3xl text-sm leading-relaxed text-muted-foreground">{answer}</p></details>)}
        </section>
      </main>
      <footer className="flex flex-wrap justify-between gap-4 border-t border-border py-6 text-xs text-muted-foreground">
        <p>By Vedansh Mehrotra. An independent companion; not affiliated with LeetCode.</p>
        <div className="flex flex-wrap gap-5"><a href="https://addons.mozilla.org/en-US/firefox/addon/pathforge-companion/privacy/" className="hover:text-foreground">Privacy policy</a><a href="mailto:mehrotravedansh2006@gmail.com" className="hover:text-foreground">Support</a><a href="https://github.com/vedanshmehrotra/PathForge-v2" className="hover:text-foreground">Source on GitHub</a></div>
      </footer>
    </div>
  )
}
