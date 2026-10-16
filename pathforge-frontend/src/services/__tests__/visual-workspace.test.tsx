import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { PracticeFootprint } from '../../../components/practice-footprint'
import { ProductTour } from '../../../components/product-tour'
import { BrandMark } from '../../../components/brand-mark'

const records = [
  { topic: 'sliding_window_fixed', attempt_count: 12 },
  { topic: 'hash_map_lookup', attempt_count: 4 },
  { topic: 'binary_search_standard', attempt_count: 8 },
  { topic: 'union_find', attempt_count: 2 },
  { topic: 'dfs_recursive', attempt_count: 6 },
]
const chart = (selected: string[], data = records) => renderToStaticMarkup(createElement(PracticeFootprint, { records: data, selected }))

describe('an expressive workspace with truthful visuals', () => {
  it('only plots selected saved counts without a fabricated skill score or timeline', () => {
    const html = chart(['hash_map_lookup', 'binary_search_standard'])
    expect(html).toContain('hash map lookup: 4 recorded attempts')
    expect(html).toContain('binary search standard: 8 recorded attempts')
    expect(html).not.toContain('sliding window fixed')
    expect(html).toContain('not a progress timeline')
    expect(html).not.toMatch(/mastery|role="progressbar"/)
    expect(html.replace(/<[^>]*>/g, '')).not.toContain('%')
  })

  it('does not convert missing records or malformed counts into zeroes', () => {
    const html = chart(['missing', 'hash_map_lookup'], [{ topic: 'hash_map_lookup', attempt_count: Number.NaN }])
    expect(html).toContain('Attempt counts are not available')
    expect(html).not.toContain('0 recorded attempts')
  })

  it('keeps a genuine zero distinguishable from unavailable data', () => {
    expect(chart(['hash_map_lookup'], [{ topic: 'hash_map_lookup', attempt_count: 0 }])).toContain('0 recorded attempts')
  })

  it('caps the chart at four unique topics', () => {
    const html = chart(['hash_map_lookup', 'hash_map_lookup', 'sliding_window_fixed', 'binary_search_standard', 'union_find', 'dfs_recursive'])
    expect((html.match(/class="topic-dot /g) ?? [])).toHaveLength(4)
    expect(html).not.toContain('dfs recursive')
  })

  it('explains an intentionally empty selection', () => {
    expect(chart([])).toContain('Choose up to four topics')
  })

  it('offers controllable illustrative slides without presenting a live diagnosis', () => {
    const html = renderToStaticMarkup(createElement(ProductTour))
    expect(html).toContain('Illustrative product tour')
    expect(html).toContain('Play product tour')
    expect(html).toContain('Product tour slides')
    expect(html).toContain('Illustrative Python snippet')
    expect(html).toContain('not a submitted analysis')
    expect(html).not.toMatch(/CONFIRMED|confidence|FULL_MATCH/)
  })

  it('uses the app mark instead of an unrelated generator logo', () => {
    expect(renderToStaticMarkup(createElement(BrandMark))).toContain('/pathforge-mark.svg')
  })
})
