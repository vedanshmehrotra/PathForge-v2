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

export function ApproachComparison({ groups, legacyPatterns }: {
  groups?: SolutionApproach[]
  legacyPatterns?: CanonicalPattern[]
}) {
  const aligned = groups?.find(reviewedAlignment)
  return (
    <div className="flex flex-col gap-3" data-testid="approach-comparison">
      <p className="text-sm font-medium">
        {approachComparisonHeading(groups)}
      </p>
      <p className="text-sm text-muted-foreground">
        {aligned ? 'Pattern evidence aligns with a reviewed approach.' :
          'The available evidence and expectations do not establish reviewed approach alignment.'}
        {' '}This does not verify solution correctness or optimality.
      </p>
      {groups?.map((group, index) => {
        const tentative = group.definition_state !== 'EXPLICIT' || group.review_state !== 'REVIEWED'
        const unused = !!aligned && group.id !== aligned.id && group.family_relation === 'ONE_OF' &&
          !!group.alternative_group_id && group.alternative_group_id === aligned.alternative_group_id
        const full = reviewedAlignment(group)
        return (
          <div key={`${group.id}-${index}`} className="border-t border-border py-5">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <p className="text-sm font-medium">{group.name || `Stored group ${index + 1}`}</p>
              <Badge variant={full ? 'success' : 'outline'}>
                {tentative ? 'Tentative comparison' : full ? 'Patterns aligned' : unused ? 'Unused alternative' : 'Evidence incomplete'}
              </Badge>
              {group.family_relation === 'ONE_OF' && group.definition_state === 'EXPLICIT' && (
                <span className="text-sm text-muted-foreground">Alternative approach</span>
              )}
            </div>
            {unused && <p className="mb-2 text-sm text-muted-foreground">This alternative is not required when another accepted approach is aligned.</p>}
            <p className="mb-1 text-sm text-muted-foreground">
              {group.definition_state === 'EXPLICIT' ? 'Component patterns within this approach (combined requirements)' : 'Stored pattern labels (relationship unverified)'}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {(group.patterns ?? []).map(pattern => (
                <Badge key={pattern} variant="outline">{label(pattern)}</Badge>
              ))}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Observed here: {(group.observed_patterns ?? []).map(label).join(', ') || 'None of the listed patterns'}
            </p>
            {!!group.unobserved_patterns?.length && (
              <p className="mt-1 text-sm text-muted-foreground">
                Not observed in this approach: {group.unobserved_patterns.map(label).join(', ')}.
                {' '}This may reflect detector coverage or a different solution approach.
              </p>
            )}
            <details className="mt-2 text-sm text-muted-foreground">
              <summary className="cursor-pointer">Source and comparison limits</summary>
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
    </div>
  )
}
