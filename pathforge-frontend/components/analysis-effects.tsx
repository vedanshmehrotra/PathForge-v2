import type { AnalyzeResponse } from '@/types/api'

export function AnalysisEffects({ result }: { result: AnalyzeResponse }) {
  const updates = result.elo_updates ?? []
  const persisted = result.persisted
  const skipped = persisted?.skill_updates_skipped === true
  const inconsistent = skipped && (updates.length > 0 || (persisted?.elo_updates_count ?? 0) > 0 || (persisted?.gap_signals_count ?? 0) > 0)

  return (
    <section aria-label="Recorded effects" className="text-sm">
      {inconsistent ? <p className="text-warning">Update details are inconsistent. Review the recorded updates below.</p> : skipped ? (
        <><p className="font-medium">Practice saved</p><p className="mt-1 text-xs text-muted-foreground">Rating unchanged · no skill-gap changes</p></>
      ) : <>
        <p className="font-medium">Recorded effects</p>
        {updates.length ? <ul className="mt-2 space-y-1.5">
          {updates.map(update => <li key={update.pattern_id} className="flex flex-wrap items-center gap-2">
            <span className={update.delta > 0 ? 'text-mint' : update.delta < 0 ? 'text-warning' : 'text-muted-foreground'}>
              {update.delta > 0 ? '+' : ''}{Number(update.delta.toFixed(1))} Elo
            </span><span className="text-muted-foreground">{update.pattern_id.replace(/_/g, ' ')}</span>
          </li>)}
        </ul> : <p className="mt-1 text-xs text-muted-foreground">No pattern Elo updates returned.</p>}
        <p className="mt-1 text-xs text-muted-foreground">{typeof persisted?.gap_signals_count === 'number'
          ? persisted.gap_signals_count > 0 ? `${persisted.gap_signals_count} gap signals recorded; change in strength is not reported.` : 'No gap signals returned.'
          : 'Gap update status unavailable.'}</p>
        {persisted?.skill_updates_skipped == null && <p className="mt-1 text-xs text-muted-foreground">This response does not report whether skill updates were skipped.</p>}
      </>}
    </section>
  )
}
