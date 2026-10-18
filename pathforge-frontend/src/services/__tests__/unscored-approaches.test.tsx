import { beforeAll, describe, expect, it } from 'vitest'
import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { ApproachDescriptions, ApproachComparison } from '../../../components/approach-comparison'
import type { AnalyzeResponse, UnscoredApproach } from '../../types/api'

type Case = { prepare: { detail?: { approaches: UnscoredApproach[] } }; response: AnalyzeResponse }
let cases: Record<string, Case>
beforeAll(() => {
  // Block real I/O before importing any backend module, including the fixture.
  const output = execFileSync(process.env.PATHFORGE_TEST_PYTHON || 'python', ['-B', '-X', 'utf8', '-c',
    'from scripts.verify_foundation import offline\nwith offline():\n from pathforge.tests.test_unscored_approaches import build_contract_cases\n import json\n print(json.dumps(build_contract_cases()))'],
  { cwd: path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..'), encoding: 'utf8', maxBuffer: 2 * 1024 * 1024 })
  cases = JSON.parse(output)
}, 30000)

describe('descriptive approaches using real builder/resolver/API/engine payloads', () => {
  it.each(['subsets', 'brackets', 'depth', 'prefix_product'])('shows %s as a descriptive proposal, never missing requirements', name => {
    const html = renderToStaticMarkup(createElement(ApproachDescriptions, { approaches: cases[name].prepare.detail!.approaches }))
    expect(html).toContain('comparison unsupported')
    expect(html).toContain('not compared or scored')
    expect(html).not.toContain('<table')
    expect(html).not.toContain('Not observed')
    expect(html).not.toContain('Patterns aligned')
  })

  it('keeps supported comparison and unsupported alternative visibly distinct', () => {
    const info = cases.mixed.response.problem_info!
    const compared = renderToStaticMarkup(createElement(ApproachComparison, { groups: info.solution_groups }))
    const described = renderToStaticMarkup(createElement(ApproachDescriptions, { approaches: info.unscored_approaches }))
    expect(compared).toContain('Listed patterns observed')
    expect(compared).toContain('Complement dictionary')
    expect(compared).not.toContain('Enumerate pairs')
    expect(described).toContain('Enumerate pairs')
    expect(described).not.toContain('Not observed')
    expect(cases.mixed.response.persisted?.skill_updates_skipped).toBe(true)
  })

  it('renders nothing for compatible older payloads', () => {
    expect(renderToStaticMarkup(createElement(ApproachDescriptions, {}))).toBe('')
  })
})
