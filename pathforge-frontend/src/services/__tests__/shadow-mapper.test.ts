/**
 * Canonical display contracts. Fixtures run the real Python engines and API
 * serializer; mutations below test incomplete or inconsistent transport data.
 */
import { beforeAll, describe, expect, it } from 'vitest'
import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { mapShadowToDisplay } from '../../services/shadow-mapper'
import { ExperimentalPanel } from '../../../components/experimental-panel'
import type { ShadowAnalysisResult } from '../../types/api'

type Case = { code: string; raw: Record<string, any>; response: { shadow_analysis: ShadowAnalysisResult } }
let cases: Record<string, Case>
beforeAll(() => {
  const output = execFileSync(process.env.PATHFORGE_TEST_PYTHON || 'python',
    ['-B', '-X', 'utf8', '-m', 'pathforge.tests.test_shadow_display_contract'],
    { cwd: path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..'),
      encoding: 'utf8', maxBuffer: 2 * 1024 * 1024 })
  cases = JSON.parse(output)
}, 30000)

const copy = (name: string) => structuredClone(cases[name].response.shadow_analysis)

describe('canonical display using actual engine output', () => {
  it('preserves a confirmed, eligible binary-search conclusion', () => {
    const data = mapShadowToDisplay(copy('bs_renamed_vars'))
    expect(data.status).toBe('likely_match')
    expect(data.statusLabel).toBe('Observed strategy')
    expect(data.approaches).toEqual(['Binary Search'])
    expect(data.confidence).toBe('High')
    expect(data.explanation).not.toMatch(/solution matches|solution follows|correct solution/i)
  })

  it.each([
    ['hash_two_sum(self)', 'PROVISIONAL', 'Hash lookup'],
    ['ps_not_prefix_just_sum', 'UNRESOLVED', 'Running total'],
  ])('does not promote %s despite legacy confirmation', (name, state, technique) => {
    expect(cases[name].raw.match_outcome.outcome).toBe('CONFIRMED')
    expect(cases[name].raw.coverage.families[0].coverage_state).toBe(state)
    const data = mapShadowToDisplay(copy(name))
    expect(data.visible).toBe(true)
    expect(data.status).toBe('not_enough_evidence')
    expect(data.approaches).toEqual(['Approach unclear'])
    expect(data.confidence).toBe('—')
    expect(data.techniques).toContain(technique)
  })

  it('uses canonical selection rather than the highest legacy evidence score', () => {
    const shadow = copy('bs_renamed_vars')
    shadow.strategy_evidence.push({ strategy_id: 'sliding_window', confidence: 1,
      strategy_version: '1', supporting_technique_ids: [], supporting_fact_ids: [], problem_context_signals: {} })
    expect(mapShadowToDisplay(shadow).approaches).toEqual(['Binary Search'])
  })

  it('works with canonical data when the older match outcome is absent', () => {
    const shadow = copy('bs_renamed_vars')
    shadow.match_outcome = null
    expect(mapShadowToDisplay(shadow).approaches).toEqual(['Binary Search'])
  })

  it('does not mutate canonical data, legacy results, or authority', () => {
    const shadow = copy('bs_renamed_vars')
    const original = JSON.stringify(shadow)
    mapShadowToDisplay(shadow)
    expect(JSON.stringify(shadow)).toBe(original)
    expect(cases.bs_renamed_vars.raw.authority.families[0].authoritative).toBe(false)
  })
})

describe('incomplete and conflicting canonical transport fails closed', () => {
  const mutations: Array<[string, (shadow: any) => void]> = [
    ['older payload', s => { delete s.coverage; delete s.strategy_selection }],
    ['missing coverage', s => { s.coverage = null }],
    ['missing selection', s => { s.strategy_selection = null }],
    ['no ground truth', s => { s.coverage.no_ground_truth = true }],
    ['provisional coverage', s => { s.coverage.families[0].coverage_state = 'PROVISIONAL' }],
    ['unresolved coverage', s => { s.coverage.families[0].coverage_state = 'UNRESOLVED' }],
    ['contradicted coverage', s => { s.coverage.families[0].coverage_state = 'CONTRADICTED' }],
    ['unmatchable coverage', s => { s.coverage.families[0].coverage_state = 'UNMATCHABLE' }],
    ['unknown state', s => { s.coverage.families[0].coverage_state = 'UNKNOWN' }],
    ['no primary', s => { s.strategy_selection.submission.selected = null }],
    ['unmatched primary', s => { s.strategy_selection.submission.selected = 'sliding_window' }],
    ['no eligibility evidence', s => { s.coverage.families[0].conclusion_eligible_present = [] }],
    ['different family primary', s => { s.strategy_selection.families[0].selected = 'sliding_window' }],
    ['missing candidate', s => { s.strategy_selection.submission.candidates = [] }],
    ['duplicate candidate', s => { s.strategy_selection.submission.candidates.push(s.strategy_selection.submission.candidates[0]) }],
    ['ambiguity', s => { s.strategy_selection.submission.ambiguity = true }],
    ['family ambiguity', s => { s.strategy_selection.families[0].ambiguity = true }],
    ['missing ambiguity flag', s => { delete s.strategy_selection.submission.ambiguity }],
    ['nonfinite confidence', s => { s.strategy_selection.submission.candidates[0].confidence = NaN }],
    ['confidence outside range', s => { s.strategy_selection.submission.candidates[0].confidence = 90 }],
    ['inconsistent confidence', s => { s.strategy_selection.families[0].candidates[0].confidence = 0.1 }],
    ['malformed families', s => { s.coverage.families = 'bad' }],
  ]
  it.each(mutations)('%s cannot establish a confirmed display', (_name, mutate) => {
    const shadow = copy('bs_renamed_vars')
    mutate(shadow)
    const data = mapShadowToDisplay(shadow)
    expect(data.status).toBe('not_enough_evidence')
    expect(data.confidence).toBe('—')
    expect(data.approaches).toEqual(['Approach unclear'])
  })

  it('does not use the coverage measurement aggregate as a global verdict', () => {
    const shadow = copy('bs_renamed_vars') as any
    shadow.coverage.aggregate_state = 'CONTRADICTED'
    shadow.coverage.families.push({ family_id: 'other', coverage_state: 'CONTRADICTED',
      conclusion_eligible_present: [], family_relation: 'ONE_OF', alternative_group_id: 'alternatives' })
    shadow.strategy_selection.families.push({ scope: 'family', family_id: 'other', selected: null,
      candidates: [], ambiguity: false, tie_resolved: false, reason_codes: ['family_contradicted'] })
    expect(mapShadowToDisplay(shadow).approaches).toEqual(['Binary Search'])
  })

  it('does not promote a selected technique when strategy evidence is absent', () => {
    const shadow = copy('hash_two_sum(self)') as any
    shadow.strategy_selection.submission.selected = 'hash_lookup'
    shadow.strategy_selection.submission.candidates = [{ concept_id: 'hash_lookup', confidence: 0.95 }]
    expect(mapShadowToDisplay(shadow).confidence).toBe('—')
  })
})

describe('visibility, confidence, and diagnostic details', () => {
  it.each([null, undefined])('hides an absent payload', shadow => {
    expect(mapShadowToDisplay(shadow).visible).toBe(false)
  })
  it('retains existing confidence bands using the selected canonical score', () => {
    for (const [score, expected] of [[0.85, 'High'], [0.6, 'Medium'], [0.3, 'Low']] as const) {
      const shadow = copy('bs_renamed_vars') as any
      shadow.strategy_selection.submission.candidates[0].confidence = score
      shadow.strategy_selection.families[0].candidates[0].confidence = score
      expect(mapShadowToDisplay(shadow).confidence).toBe(expected)
    }
  })
  it('keeps old outcome and technique evidence in diagnostic details', () => {
    const data = mapShadowToDisplay(copy('hash_two_sum(self)'))
    expect(data.developerDetails.outcome).toBe('CONFIRMED')
    expect(data.developerDetails.techniques.some(t => t.id === 'hash_lookup')).toBe(true)
    expect(data.developerDetails.extractorVersion).toBeTruthy()
  })
  it('uses readable labels for visible technique evidence', () => {
    const data = mapShadowToDisplay(copy('bs_renamed_vars'))
    expect(data.techniques).toContain('Candidate selection')
    expect(data.techniques.every(name => !name.includes('_'))).toBe(true)
  })
})

describe('actual experimental panel rendering', () => {
  it.each(['hash_two_sum(self)', 'ps_not_prefix_just_sum'])('renders %s without a confident strategy claim', name => {
    const html = renderToStaticMarkup(createElement(ExperimentalPanel, { shadowAnalysis: copy(name) }))
    expect(html).toContain('Not enough evidence')
    expect(html).toContain('Approach unclear')
    expect(html).toContain('Detected techniques')
    expect(html).not.toContain('Confidence:')
    expect(html).not.toContain('Observed strategy')
    expect(html).toContain('Developer details')
    expect(html).not.toContain('Legacy outcome') // Still collapsed.
  })
  it('renders confirmed evidence with a correctness/scoring distinction', () => {
    const html = renderToStaticMarkup(createElement(ExperimentalPanel, { shadowAnalysis: copy('bs_renamed_vars') }))
    expect(html).toContain('Observed strategy')
    expect(html).toContain('Binary Search')
    expect(html).toContain('Confidence: High')
    expect(html).toContain('does not verify solution correctness or scoring eligibility')
  })
})
