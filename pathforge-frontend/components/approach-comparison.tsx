import { Badge } from '@/components/ui/badge'
import { Check, Minus } from 'lucide-react'
import type { CanonicalPattern, SolutionApproach, UnscoredApproach } from '@/types/api'

const label = (name: string) => name.replace(/_/g, ' ')

export function ApproachDescriptions({ approaches }: { approaches?: UnscoredApproach[] }) {
  if (!approaches?.length) return null
  return <section aria-label="Approaches outside comparison coverage"><details className="space-y-3 border-t border-border py-4">
    <summary className="cursor-pointer text-sm font-medium">Other proposed approaches · comparison unsupported</summary>
    {approaches.map(approach => <div key={approach.id} className="space-y-1 text-sm">
      <p className="font-medium">{approach.name}</p>
      <p className="text-muted-foreground">{approach.description}</p>
      <p className="text-xs text-muted-foreground">Coverage limit: {approach.coverage_limit}</p>
    </div>)}
    <p className="text-xs text-muted-foreground">Unverified descriptions, not missing skills or solution verdicts. These approaches are not compared or scored.</p>
  </details></section>
}

function completeComparison(group: SolutionApproach): boolean {
  return Array.isArray(group.patterns) && group.patterns.length > 0 &&
    Array.isArray(group.observed_patterns) && Array.isArray(group.unobserved_patterns) &&
    group.unobserved_patterns.length === 0 &&
    group.patterns.every(pattern => typeof pattern === 'string' && group.observed_patterns.includes(pattern))
}

function reviewedAlignment(group: SolutionApproach): boolean {
  return group.definition_state === 'EXPLICIT' && group.review_state === 'REVIEWED' &&
    group.pattern_evidence_state !== 'UNAVAILABLE' &&
    group.comparison_state === 'FULL_MATCH' && completeComparison(group)
}

function proposedOverlap(group: SolutionApproach): boolean {
  return group.definition_state === 'EXPLICIT' && group.review_state === 'UNREVIEWED' &&
    group.pattern_evidence_state === 'ALL_OBSERVED' &&
    group.comparison_state === 'FULL_MATCH' && completeComparison(group)
}

function legacyOverlap(group: SolutionApproach): boolean {
  // A complete listed-pattern overlap does not verify the stored relationship.
  return group.definition_state === 'LEGACY_UNSPECIFIED' && group.review_state === 'UNREVIEWED' &&
    group.pattern_evidence_state === 'UNAVAILABLE' &&
    group.comparison_state === 'FULL_MATCH' && completeComparison(group)
}

export function approachComparisonHeading(groups?: SolutionApproach[]): string {
  return groups?.some(reviewedAlignment) ? 'Pattern alignment observed' :
    groups?.some(proposedOverlap) ? 'Listed patterns observed — proposed approach' :
    groups?.some(legacyOverlap) ? 'Listed patterns detected — stored approach unverified' :
    groups?.length ? 'Inconclusive comparison' : 'Comparison unavailable'
}

export function hasCompletePatternComparison(groups?: SolutionApproach[]): boolean {
  return groups?.some(group => reviewedAlignment(group) || proposedOverlap(group) || legacyOverlap(group)) ?? false
}

// Provenance remains inspectable, separate from the user's comparison result.
export function ApproachComparisonDetails({ groups }: { groups?: SolutionApproach[] }) {
  if (!groups?.length) return null
  return <div className="mt-5 space-y-5 text-sm text-muted-foreground">
    {groups.map((group, index) => <div key={`${group.id}-${index}`}>
      <h3 className="mb-2 font-medium text-foreground">{group.name || `Stored group ${index + 1}`}</h3>
      <p>{group.definition_state === 'EXPLICIT' ? 'Components are combined requirements.' : 'The relationship between these stored labels is unverified.'}</p>
      <p>Expectation authority: {group.authority_tier || 'Unspecified'}</p>
      <p>Provenance: {group.provenance?.join(', ') || 'Not recorded'}</p>
      <p>Canonical concepts: {group.required?.map(label).join(', ') || 'Not available'}</p>
      {!!group.optional?.length && <p>Optional concepts: {group.optional.map(label).join(', ')}</p>}
      {!!group.excluded?.length && <p>Excluded concepts: {group.excluded.map(label).join(', ')}</p>}
      {group.limitations?.map((limitation, i) => <p key={i}>{limitation}</p>)}
    </div>)}
  </div>
}

export function ApproachComparison({ groups, legacyPatterns, showSummary = true }: {
  groups?: SolutionApproach[]
  legacyPatterns?: CanonicalPattern[]
  showSummary?: boolean
}) {
  const aligned = groups?.find(reviewedAlignment)
  const proposed = groups?.find(proposedOverlap)
  return (
    <div className="flex flex-col gap-3" data-testid="approach-comparison">
      {showSummary && <p className="text-sm font-medium">{approachComparisonHeading(groups)}</p>}
      {groups?.map((group, index) => {
        const unused = !!aligned && group.id !== aligned.id && group.family_relation === 'ONE_OF' &&
          !!group.alternative_group_id && group.alternative_group_id === aligned.alternative_group_id
        const full = reviewedAlignment(group)
        const overlap = full || proposedOverlap(group) || legacyOverlap(group)
        const otherProposed = !aligned && !!proposed && proposed.id !== group.id &&
          group.definition_state === 'EXPLICIT' && group.review_state === 'UNREVIEWED' &&
          group.family_relation === 'ONE_OF' && !!group.alternative_group_id &&
          group.alternative_group_id === proposed.alternative_group_id &&
          ['ALL_OBSERVED', 'SOME_OBSERVED', 'NONE_OBSERVED'].includes(group.pattern_evidence_state ?? '')
        return (
          <div key={`${group.id}-${index}`} className="detail-enter border-t border-border py-4">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <p className="text-sm font-medium">{group.definition_state === 'EXPLICIT' ? group.name || `Approach ${index + 1}` : `Stored patterns ${index + 1}`}</p>
              <Badge variant={overlap ? 'success' : 'outline'}>
                {overlap ? 'All patterns detected' : unused ? 'Unused alternative' : group.review_state === 'CONFLICT' ? 'Comparison limited' : 'Incomplete comparison'}
              </Badge>
              {(group.definition_state !== 'EXPLICIT' || group.review_state !== 'REVIEWED') && <span className="text-xs text-muted-foreground">{group.definition_state === 'EXPLICIT' ? 'Proposed approach' : 'Unverified comparison'}</span>}
              {group.family_relation === 'ONE_OF' && group.definition_state === 'EXPLICIT' && (
                <span className="text-sm text-muted-foreground">Alternative approach</span>
              )}
            </div>
            {unused && <p className="mb-2 text-sm text-muted-foreground">This alternative is not required.</p>}
            {otherProposed && <p className="mb-2 text-sm text-muted-foreground">Other proposed alternative</p>}
            {group.definition_state === 'EXPLICIT' && <p className="mb-3 text-xs text-muted-foreground">These patterns are used together.</p>}
            <table className="w-full table-fixed text-left text-sm" aria-label={`Pattern comparison ${index + 1}`}>
              <thead className="text-xs text-muted-foreground"><tr><th scope="col" className="w-3/5 pb-2 pr-3 font-normal">Stored patterns</th><th scope="col" className="pb-2 font-normal">Your code</th></tr></thead>
              <tbody>{(group.patterns ?? []).map(pattern => {
                const observed = (group.observed_patterns ?? []).includes(pattern)
                const unobserved = (group.unobserved_patterns ?? []).includes(pattern)
                return <tr key={pattern} className="border-t border-border/60">
                  <th scope="row" className="break-words py-2.5 pr-3 font-normal">{label(pattern)}</th>
                  <td className={`py-2.5 ${unused ? 'text-muted-foreground' : observed && !unobserved ? 'text-mint' : 'text-muted-foreground'}`}>
                    <span className="inline-flex items-center gap-2">
                      {!unused && !otherProposed && (observed && !unobserved
                        ? <Check aria-hidden="true" data-testid="pattern-detected-icon" className="size-4 shrink-0" />
                        : <Minus aria-hidden="true" className="size-4 shrink-0" />)}
                      {unused ? 'Not required' : otherProposed ? 'Other proposed option' : observed && !unobserved ? 'Detected' : unobserved && !observed ? 'Not detected' : 'Uncertain'}
                    </span>
                  </td>
                </tr>
              })}</tbody>
            </table>
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
