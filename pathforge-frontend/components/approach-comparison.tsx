import { Badge } from '@/components/ui/badge'
import type { CanonicalPattern, SolutionApproach } from '@/types/api'

const label = (name: string) => name.replace(/_/g, ' ')

function completeComparison(group: SolutionApproach): boolean {
  return Array.isArray(group.patterns) && group.patterns.length > 0 &&
    Array.isArray(group.observed_patterns) && Array.isArray(group.unobserved_patterns) &&
    group.unobserved_patterns.length === 0 &&
    group.patterns.every(pattern => typeof pattern === 'string' && group.observed_patterns.includes(pattern))
}

function reviewedAlignment(group: SolutionApproach): boolean {
  return group.definition_state === 'EXPLICIT' && group.review_state === 'REVIEWED' &&
    group.comparison_state === 'FULL_MATCH' && completeComparison(group)
}

export function approachComparisonHeading(groups?: SolutionApproach[]): string {
  return groups?.some(reviewedAlignment) ? 'Pattern alignment observed' :
    groups?.length ? 'Inconclusive comparison' : 'Comparison unavailable'
}

export function ApproachComparison({ groups, legacyPatterns, showSummary = true }: {
  groups?: SolutionApproach[]
  legacyPatterns?: CanonicalPattern[]
  showSummary?: boolean
}) {
  const aligned = groups?.find(reviewedAlignment)
  return (
    <div className="flex flex-col gap-3" data-testid="approach-comparison">
      {showSummary && <p className="text-sm font-medium">{approachComparisonHeading(groups)}</p>}
      {groups?.map((group, index) => {
        const tentative = group.definition_state !== 'EXPLICIT' || group.review_state !== 'REVIEWED'
        const unused = !!aligned && group.id !== aligned.id && group.family_relation === 'ONE_OF' &&
          !!group.alternative_group_id && group.alternative_group_id === aligned.alternative_group_id
        const full = reviewedAlignment(group)
        return (
          <div key={`${group.id}-${index}`} className="detail-enter border-t border-border py-4">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <p className="text-sm font-medium">{group.definition_state === 'EXPLICIT' ? group.name || `Approach ${index + 1}` : `Stored expectation ${index + 1}`}</p>
              <Badge variant={full ? 'success' : 'outline'}>
                {tentative ? 'Tentative comparison' : full ? 'Patterns aligned' : unused ? 'Unused alternative' : 'Evidence incomplete'}
              </Badge>
              {group.family_relation === 'ONE_OF' && group.definition_state === 'EXPLICIT' && (
                <span className="text-sm text-muted-foreground">Alternative approach</span>
              )}
            </div>
            {unused && <p className="mb-2 text-sm text-muted-foreground">This alternative is not required when another accepted approach is aligned.</p>}
            <p className="mb-3 text-xs text-muted-foreground">{group.definition_state === 'EXPLICIT' ? 'Components are combined requirements.' : 'Unreviewed relationship between stored labels.'}</p>
            <table className="w-full table-fixed text-left text-sm" aria-label={`Pattern comparison ${index + 1}`}>
              <thead className="text-xs text-muted-foreground"><tr><th scope="col" className="w-3/5 pb-2 pr-3 font-normal">Stored expectation</th><th scope="col" className="pb-2 font-normal">Detected evidence</th></tr></thead>
              <tbody>{(group.patterns ?? []).map(pattern => {
                const observed = (group.observed_patterns ?? []).includes(pattern)
                const unobserved = (group.unobserved_patterns ?? []).includes(pattern)
                return <tr key={pattern} className="border-t border-border/60">
                  <th scope="row" className="break-words py-2.5 pr-3 font-normal">{label(pattern)}</th>
                  <td className={`py-2.5 ${unused ? 'text-muted-foreground' : observed && !unobserved ? 'text-mint' : 'text-muted-foreground'}`}>
                    {unused ? 'Not required' : observed && !unobserved ? 'Observed' : unobserved && !observed ? 'Not observed' : 'Uncertain'}
                  </td>
                </tr>
              })}</tbody>
            </table>
            <details className="mt-2 text-sm text-muted-foreground">
              <summary className="cursor-pointer">Source and comparison limits</summary>
              <p>Stored name: {group.name || 'Unspecified'}</p>
              <p>Expectation authority: {group.authority_tier || 'Unspecified'}</p>
              <p>Provenance: {group.provenance?.join(', ') || 'Not recorded'}</p>
              <p>Canonical concepts: {group.required?.map(label).join(', ') || 'Not available'}</p>
              {!!group.optional?.length && <p>Optional concepts: {group.optional.map(label).join(', ')}</p>}
              {!!group.excluded?.length && <p>Excluded concepts: {group.excluded.map(label).join(', ')}</p>}
              {group.limitations?.map((limitation, i) => <p key={i}>{limitation}</p>)}
            </details>
          </div>
        )
      })}
      {!groups?.length && !!legacyPatterns?.length && (
        <div>
          <p className="mb-1 text-sm text-muted-foreground">Stored labels (relationship unverified)</p>
          <div className="flex flex-wrap gap-1.5">
            {legacyPatterns.map((pattern, i) => <Badge key={`${pattern.name}-${i}`} variant="outline">{label(pattern.name)}</Badge>)}
          </div>
        </div>
      )}
      <p className="text-xs leading-relaxed text-muted-foreground">Not observed can mean limited detector coverage or an unsuitable stored expectation. Pattern alignment does not prove correctness.</p>
    </div>
  )
}
