import type { AuthProfile } from '@/types/api'

type PracticeRecord = Pick<AuthProfile['profiles'][number], 'topic' | 'attempt_count'>
const COLORS = ['var(--mint)', 'var(--sky)', 'var(--amber)', '#b4b8c2']

export function PracticeFootprint({ records, selected }: { records: PracticeRecord[]; selected: string[] }) {
  // Missing counts must not become zeroes or invented learner-state estimates.
  const series = [...new Set(selected)].slice(0, 4).flatMap(topic => {
    const record = records.find(item => item.topic === topic)
    return record && Number.isFinite(record.attempt_count) && record.attempt_count >= 0 ? [record] : []
  })
  const maximum = Math.max(1, ...series.map(record => record.attempt_count))
  return (
    <figure aria-label="Selected topics: recorded attempt comparison" className="min-w-0">
      <div className="mb-7 flex justify-between text-[11px] text-muted-foreground" aria-hidden="true"><span>Less recorded</span><span>More recorded</span></div>
      {series.length ? <div className="space-y-7">
        {series.map((record, index) => <div key={record.topic} className="grid min-w-0 grid-cols-[minmax(95px,0.7fr)_minmax(0,1.6fr)] items-center gap-4">
          <span className="break-words text-xs capitalize text-muted-foreground">{record.topic.replace(/_/g, ' ')}</span>
          <div className="relative h-7 border-b border-dashed border-border">
            <span className="absolute inset-y-0 left-1/4 border-l border-border/60" /><span className="absolute inset-y-0 left-1/2 border-l border-border/60" /><span className="absolute inset-y-0 left-3/4 border-l border-border/60" />
            <button type="button" aria-label={`${record.topic.replace(/_/g, ' ')}: ${record.attempt_count} recorded attempts`}
              className="topic-dot group absolute top-[14px] size-8 -translate-x-1/2 -translate-y-1/2 rounded-full focus-visible:outline-offset-2"
              style={{ left: `${4 + record.attempt_count / maximum * 92}%`, color: COLORS[index] }}>
              <span style={record.attempt_count / maximum > 0.5 ? { right: 0 } : { left: 0 }} className="pointer-events-none absolute bottom-5 z-10 whitespace-nowrap rounded border border-border bg-popover px-2 py-1 text-xs text-foreground opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">{record.attempt_count} recorded attempts</span>
            </button>
          </div>
        </div>)}
      </div> : <p className="py-6 text-sm text-muted-foreground">{selected.length ? 'Attempt counts are not available for these topics. Choose a topic with a saved practice record.' : 'Choose up to four topics to draw your practice footprint.'}</p>}
      <figcaption className="mt-7 text-xs leading-relaxed text-muted-foreground">Saved attempts, not a skill rating. This compares selected topics; it is not a progress timeline.</figcaption>
    </figure>
  )
}
