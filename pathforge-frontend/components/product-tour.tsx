'use client'

import { useEffect, useState } from 'react'
import { ArrowRight, Braces, Compass, Layers2, Pause, Play } from 'lucide-react'
import Image from 'next/image'

const STEPS = [
  { label: 'Inspect', title: 'The window moves. Its width stays fixed.', description: 'Follow the relationship between incoming and outgoing elements, beyond the names of your variables.' },
  { label: 'Compare', title: 'Different approaches. One clear comparison.', description: 'Keep combined requirements together, and alternative solutions apart. See where your evidence aligns.' },
  { label: 'Practise', title: 'Keep the next step within reach.', description: 'Return to something familiar or explore a different problem, using your recorded practice as context.' },
]

const COMPANION_STEPS = [
  { label: 'Understand', title: 'A pattern name, with an explanation.', description: 'Your Python code is read from LeetCode. Tap a detected pattern to understand the structure PathForge spotted.', image: 'patterns.png' },
  { label: 'Progress', title: 'See eligible XP arrive.', description: 'A real rating change briefly fills the pattern bar. Rechecks never replay the reward; unscored practice is still saved.', image: 'level-up.png' },
  { label: 'Retry', title: 'A wrong answer is room to try again.', description: 'No XP is lost for a failed submission. Fix and resubmit; any follow-up suggestions are tied to the current problem’s topic.', image: 'retry.png' },
]

export function ProductTour({ companion = false }: { companion?: boolean }) {
  const steps = companion ? COMPANION_STEPS : STEPS
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [reduced, setReduced] = useState(true)
  const [hovered, setHovered] = useState(false)
  const [focused, setFocused] = useState(false)
  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => { setReduced(media.matches); setPlaying(!media.matches) }
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])
  useEffect(() => {
    if (!playing || reduced || hovered || focused) return
    const timer = window.setInterval(() => {
      if (!document.hidden) setIndex(previous => (previous + 1) % steps.length)
    }, 7000)
    return () => window.clearInterval(timer)
  }, [playing, reduced, hovered, focused, steps.length])
  const step = steps[index]

  return (
    <section aria-label="Illustrative product tour" className="min-w-0 border-y border-border lg:border-y-0 lg:border-l lg:pl-8"
      onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
      onFocusCapture={() => setFocused(true)}
      onBlurCapture={event => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setFocused(false) }}>
      <div className="flex min-h-14 items-center justify-between gap-3 border-b border-border py-3">
        <span className="eyebrow"><span className="size-2 rounded-full bg-mint" />{companion ? 'Inside the companion' : 'A closer look at PathForge'}</span>
        <button type="button" onClick={() => setPlaying(value => !value)} disabled={reduced}
          aria-label={playing ? 'Pause product tour' : 'Play product tour'}
          title={reduced ? 'Automatic motion is off for your reduced-motion preference' : 'Control automatic slides'}
          className="flex size-9 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary disabled:opacity-50">
          {playing ? <Pause className="size-4" /> : <Play className="size-4" />}
        </button>
      </div>
      <div className="min-h-[365px] py-6" aria-live={playing ? 'off' : 'polite'} aria-atomic="true">
        <div key={index} className="detail-enter">
          {companion ? <figure>
            <Image src={`/companion/${COMPANION_STEPS[index].image}`} alt={`Companion ${COMPANION_STEPS[index].label.toLowerCase()} screen with illustrative sample data`} width={400} height={900} loading={index === 0 ? 'eager' : 'lazy'} className="mx-auto max-h-[570px] w-auto max-w-full rounded-md border border-border object-contain" />
            <figcaption className="mt-3 text-xs text-muted-foreground">Actual extension interface · illustrative sample data</figcaption>
          </figure> : index === 0 ? <>
            <div className="mb-6 flex flex-wrap justify-center gap-2" aria-label="Illustrative fixed window over a sequence">
              {[2, 4, 1, 7, 3, 6].map((value, i) => <span key={i} className={`window-cell ${i > 0 && i < 4 ? 'border-mint/60 bg-mint/10 text-mint' : 'text-muted-foreground'}`}>{value}</span>)}
            </div>
            <div className="overflow-hidden rounded-md border border-border bg-card">
              <div className="flex items-center gap-2 border-b border-border px-4 py-2 text-xs text-muted-foreground"><Braces className="size-3.5 text-mint" />window.py<span className="ml-auto">Python</span></div>
              <pre className="overflow-x-auto p-4 font-mono text-xs leading-[1.9] sm:text-sm"><code><span className="text-sky">window</span>{' = sum(values[:width])\nfor index in range(width, len(values)):\n'}<span className="text-mint">{'    window += values[index]'}</span>{'\n'}<span className="text-amber">{'    window -= values[index - width]'}</span></code></pre>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">Illustrative Python snippet · not a submitted analysis</p>
          </> : index === 1 ? <div className="flex min-h-[237px] flex-col justify-center gap-4">
            <div className="border-l border-border py-3 pl-4"><p className="eyebrow text-mint"><Layers2 className="size-4" />One approach</p><p className="mt-2 text-sm">Maintain a fixed window</p><p className="mt-1 text-xs text-muted-foreground">Incoming element + outgoing element</p></div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground"><span className="h-px flex-1 bg-border" />or<span className="h-px flex-1 bg-border" /></div>
            <div className="border-l border-border py-3 pl-4"><p className="eyebrow text-sky"><Layers2 className="size-4" />An alternative</p><p className="mt-2 text-sm">Use prefix differences</p><p className="mt-1 text-xs text-muted-foreground">A different route to the same problem</p></div>
          </div> : <div className="flex min-h-[237px] flex-col justify-center gap-3">
            {[['Revisit', 'Return to a familiar structure', 'mint'], ['Explore', 'Work with a different problem', 'sky'], ['Make it yours', 'Adjust difficulty when you want', 'amber']].map(([label, title, color]) => <div key={label} className="flex items-center gap-4 border-b border-border py-4"><Compass className={`size-5 shrink-0 tone-${color}`} /><div><p className={`text-xs font-semibold tone-${color}`}>{label}</p><p className="mt-1 text-sm">{title}</p></div><ArrowRight className="ml-auto size-4 text-muted-foreground" /></div>)}
          </div>}
          <h2 className="mt-6 text-xl font-semibold tracking-tight">{step.title}</h2>
          <p className="mt-2 max-w-lg text-sm leading-relaxed text-muted-foreground">{step.description}</p>
        </div>
      </div>
      <div className="flex gap-2 border-t border-border py-4" role="group" aria-label="Product tour slides">
        {steps.map((item, i) => <button key={item.label} type="button" aria-pressed={i === index}
          onClick={() => { setIndex(i); setPlaying(false) }}
          className={`flex min-h-10 flex-1 items-center justify-center gap-2 rounded-md text-xs font-semibold transition-colors ${i === index ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:bg-secondary/60'}`}>
          <span className={`size-1.5 rounded-full ${i === index ? 'bg-mint' : 'bg-muted-foreground/40'}`} />{item.label}
        </button>)}
      </div>
    </section>
  )
}
