import { describe, expect, it } from 'vitest'
import { problemUrl } from '../recommendations'

describe('problem destinations are explicit and restricted', () => {
  it.each([null, undefined, '', 704, 'javascript:alert(1)',
    'http://leetcode.com/problems/two-sum/', 'https://leetcode.com.evil.invalid/problems/two-sum/',
    'https://user:secret@leetcode.com/problems/two-sum/', 'https://leetcode.com:8443/problems/two-sum/',
    'https://leetcode.com/problems/two-sum/?next=elsewhere', 'https://leetcode.com/problems/two-sum/#details',
    'https://leetcode.com/problemset/', 'https://leetcode.com\\@evil.invalid/problems/two-sum/',
    'https://leetcode.com/problems/two-\nsum/',
  ])('rejects unsafe or missing destination %s', value => expect(problemUrl(value)).toBeNull())

  it('uses the stored slug and canonicalizes the allowed host', () => {
    expect(problemUrl('https://www.leetcode.com/problems/two-sum')).toBe('https://leetcode.com/problems/two-sum/')
  })
})
