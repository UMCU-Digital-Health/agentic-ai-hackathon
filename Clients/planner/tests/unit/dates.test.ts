import { describe, expect, it } from 'vitest'
import { parseApiDate, toApiDate } from '../../src/api/dates'

describe('the API date boundary', () => {
  it('reads a naive backend datetime as local clinic time', () => {
    const parsed = parseApiDate('2026-08-27T09:30:00')

    expect(parsed.getHours()).toBe(9)
    expect(parsed.getMinutes()).toBe(30)
    expect(parsed.getDate()).toBe(27)
  })

  it('writes a Date back in the naive format the API expects', () => {
    const value = new Date(2026, 7, 27, 9, 30, 0)

    expect(toApiDate(value)).toBe('2026-08-27T09:30:00')
  })

  it('round-trips without drifting', () => {
    const original = '2026-08-27T14:45:00'

    expect(toApiDate(parseApiDate(original))).toBe(original)
  })

  it('round-trips across a DST transition', () => {
    // Local clock time is preserved on both sides of the spring-forward date.
    const beforeDst = '2026-03-28T09:00:00'
    const afterDst = '2026-03-30T09:00:00'

    expect(toApiDate(parseApiDate(beforeDst))).toBe(beforeDst)
    expect(toApiDate(parseApiDate(afterDst))).toBe(afterDst)
  })
})
