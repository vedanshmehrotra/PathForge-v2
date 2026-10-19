import { beforeAll, describe, expect, it, vi } from 'vitest'
import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { AnalysisEffects } from '../../../components/analysis-effects'
import { AnalysisView } from '../../../components/analysis-view'
import { ApproachComparison, ApproachComparisonDetails } from '../../../components/approach-comparison'
import type { AnalyzeResponse } from '../../types/api'

const fixture = vi.hoisted(() => ({ response: null as AnalyzeResponse | null }))
vi.mock('@/auth/AuthProvider', () => ({ useAuth: () => ({ profile: { user_id: 7 } }) }))
vi.mock('@/hooks/useApi', () => ({
  useAnalyzeCode: () => ({ result: fixture.response, loading: false, error: null, errorCode: null, run: vi.fn() }),
  usePrepareProblem: () => ({ result: null, loading: false, error: null, run: vi.fn(), clear: vi.fn() }),
}))

let actual: AnalyzeResponse
let cycle: AnalyzeResponse
let conflict: AnalyzeResponse
beforeAll(() => {
  const output = execFileSync(process.env.PATHFORGE_TEST_PYTHON || 'python',
    ['-B', '-X', 'utf8', '-m', 'pathforge.tests.test_analysis_feedback'],
    { cwd: path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..'), encoding: 'utf8' })
  actual = JSON.parse(output).response
  // The user's ordinary Floyd implementation, parsed by the real engines.
  // This reproduces the screenshot's legacy labels without reading its DB row.
  const engineCases = JSON.parse(execFileSync(process.env.PATHFORGE_TEST_PYTHON || 'python', ['-B', '-X', 'utf8', '-c', `
from scripts.verify_foundation import offline
with offline():
 from pathforge.api.services.analysis import run_analysis
 from pathforge.api.services.approaches import describe_approaches
 from pathforge.services.problem_resolver import resolve_problem
 from pathforge.tests.test_problem_preparation_boundary import MemoryConnection
 import json
 code = '''class Solution:
    def hasCycle(self, head: Optional[ListNode]) -> bool:
        fast=head
        slow=head
        while fast and fast.next:
            fast=fast.next.next
            slow=slow.next
            if fast==slow:
                return True
        return False
'''
 groups = [{'id': 'legacy', 'patterns': ['fast_slow_pointers', 'two_pointers_same'],
            'required': ['forward_pointer_advance'], 'authority_tier': 'llm_proposed',
            'evidence': 'llm_proposed'}]
 result = run_analysis(code, accepted_solution_groups=groups)
 info = {'title': 'Linked List Cycle', 'canonical_patterns': [],
         'solution_groups': [g.model_dump() for g in describe_approaches(groups, result['ast'])]}
 cycle = {**result, 'problem_info': info}
 # Reproduce the verified legacy Add Two Numbers reconciliation conflict.
 # Representative carry implementation, not the screenshot's partial source.
 source = '''def add(a, b):
    dummy = Node(0)
    tail = dummy
    carry = 0
    while a or b or carry:
        total = carry
        if a:
            total += a.val
            a = a.next
        if b:
            total += b.val
            b = b.next
        carry = total // 10
        tail.next = Node(total % 10)
        tail = tail.next
    return dummy.next
'''
 conn = MemoryConnection(problem={'id': 2, 'title': 'Add Two Numbers', 'difficulty': 'Medium',
    'pattern': ['two_pointers_same']}, ground_truth={'patterns': ['linked_list_reversal'],
    'confidence': {}, 'solution_groups': [{'id': 'g0', 'patterns': ['linked_list_reversal'],
    'evidence': 'llm_proposed'}], 'validation_status': 'llm_proposed'})
 ctx = resolve_problem(conn, leetcode_id=2, allow_preparation=False)
 result = run_analysis(source, accepted_solution_groups=ctx.accepted_solution_groups)
 result['problem_info'] = {'title': 'Add Two Numbers', 'canonical_patterns': [],
    'solution_groups': [g.model_dump() for g in describe_approaches(ctx.accepted_solution_groups, result['ast'])]}
 assert not conn.writes
 print(json.dumps({'cycle': cycle, 'conflict': result}))
`], { cwd: path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..'), encoding: 'utf8' }))
  cycle = engineCases.cycle
  conflict = engineCases.conflict
}, 30000)

const effects = (response: AnalyzeResponse) => renderToStaticMarkup(createElement(AnalysisEffects, { result: response }))

describe('concise and truthful analysis feedback', () => {
  it('gives a complete pattern overlap a visual success state without calling the code correct', () => {
    fixture.response = cycle
    const html = renderToStaticMarkup(createElement(AnalysisView))
    expect(html).toContain('Patterns match')
    expect(html).toContain('data-result-state="match"')
    expect(html).toContain('data-testid="pattern-detected-icon"')
    const summary = html.match(/<section id="analysis-summary"[\s\S]*?<\/section>/)![0]
    expect(summary).not.toMatch(/approach is correct|solution is correct/i)
  })

  it('keeps provenance and FAQ copy out of the primary comparison', () => {
    const groups = cycle.problem_info!.solution_groups
    const primary = renderToStaticMarkup(createElement(ApproachComparison, { groups }))
    const details = renderToStaticMarkup(createElement(ApproachComparisonDetails, { groups }))
    expect(primary).not.toMatch(/How this comparison was made|What does|Provenance|Canonical concepts|Expectation authority/)
    expect(details).toContain('Expectation authority')
  })

  it('makes saving practice the primary effect rather than a no-Elo warning', () => {
    expect(effects(actual)).toContain('Practice saved')
    expect(effects(actual)).toContain('Rating unchanged')
    expect(effects(actual)).not.toContain('No Elo or gap changes')
  })

  it('shows real bracket-case engine output without calling correct code incorrect', () => {
    fixture.response = actual
    const html = renderToStaticMarkup(createElement(AnalysisView))
    expect(html).toContain('Approach comparison is limited')
    expect(html).toContain('Stored patterns')
    expect(html).toContain('Your code')
    expect(html).toContain('monotonic stack')
    expect(html).toContain('array traversal')
    expect(html).toContain('Practice saved')
    expect(html).toContain('Patterns detected')
    expect(html).toContain('do not check code correctness')
    expect(html).not.toMatch(/your code is incorrect|skill gap increased|Stored history signals/i)
  })

  it('distinguishes detected Floyd patterns from unverified legacy approach structure', () => {
    const group = cycle.problem_info!.solution_groups![0]
    expect(group.comparison_state).toBe('FULL_MATCH')
    expect(group.pattern_evidence_state).toBe('UNAVAILABLE')
    expect(group.observed_patterns).toEqual(['fast_slow_pointers', 'two_pointers_same'])
    fixture.response = cycle
    const html = renderToStaticMarkup(createElement(AnalysisView))
    expect(html).toContain('Patterns match')
    expect(html).toContain('Unverified comparison')
    expect(html).not.toContain('Inconclusive comparison')
    expect(html).not.toContain('Pattern alignment observed')
    expect(html).not.toContain('Practice saved') // No persistence status in this service fixture.
  })

  it('acknowledges real detections without turning a reconciled metadata conflict into a match', () => {
    const group = conflict.problem_info!.solution_groups![0]
    expect(group.review_state).toBe('CONFLICT')
    expect(group.comparison_state).toBe('FULL_MATCH')
    expect(group.observed_patterns).toEqual(['two_pointers_same'])
    fixture.response = conflict
    const html = renderToStaticMarkup(createElement(AnalysisView))
    expect(html).toContain('Patterns detected')
    expect(html).toContain('data-result-state="detected"')
    expect(html).toContain('Comparison limited')
    expect(html).toContain('data-testid="pattern-detected-icon"')
    expect(html).not.toContain('Patterns match')
    expect(html).not.toContain('All patterns detected')
  })

  it('does not trust incomplete, conflicting or contradictory legacy overlap', () => {
    const group = cycle.problem_info!.solution_groups![0]
    for (const change of [
      { observed_patterns: [] }, { unobserved_patterns: ['fast_slow_pointers'] },
      { review_state: 'CONFLICT' as const }, { pattern_evidence_state: undefined },
    ]) {
      const html = renderToStaticMarkup(createElement(ApproachComparison, { groups: [{ ...group, ...change }] }))
      expect(html).toContain('Inconclusive comparison')
      expect(html).not.toContain('Listed patterns detected — stored approach unverified')
    }
  })

  it('uses the actual persistence skip decision for the no-change claim', () => {
    expect(actual.persisted?.skill_updates_skipped).toBe(true)
    expect(effects(actual)).toContain('Rating unchanged')
  })

  it('does not infer skipped scoring from an older payload or an inconclusive comparison', () => {
    const older = structuredClone(actual)
    delete older.persisted!.skill_updates_skipped
    expect(effects(older)).not.toContain('Rating unchanged')
    expect(effects(older)).not.toContain('Practice saved')
    expect(effects(older)).toContain('does not report whether skill updates were skipped')
  })

  it('displays returned Elo deltas, including decreases, without inventing a correctness verdict', () => {
    const scored = structuredClone(actual)
    scored.persisted!.skill_updates_skipped = false
    scored.elo_updates = [
      { pattern_id: 'prefix_sum', elo_before: 1200, elo_after: 1208, delta: 8 },
      { pattern_id: 'hash_map_lookup', elo_before: 1200, elo_after: 1196, delta: -4 },
    ]
    const html = effects(scored)
    expect(html).toContain('+8 Elo')
    expect(html).toContain('-4 Elo')
    expect(html).toContain('prefix sum')
    expect(html).not.toContain('Rating unchanged')
  })

  it('does not turn an aggregate gap count into a claim that a gap increased', () => {
    const scored = structuredClone(actual)
    scored.persisted!.skill_updates_skipped = false
    scored.persisted!.gap_signals_count = 2
    expect(effects(scored)).toContain('2 gap signals recorded; change in strength is not reported')
    expect(effects(scored)).not.toMatch(/gap increased|gap decreased/i)
  })

  it('rejects contradictory update metadata instead of asserting no changes', () => {
    const inconsistent = structuredClone(actual)
    inconsistent.persisted!.elo_updates_count = 1
    expect(effects(inconsistent)).toContain('Update details are inconsistent')
    expect(effects(inconsistent)).not.toContain('Rating unchanged')
    expect(effects(inconsistent)).not.toContain('Practice saved')
  })
})
