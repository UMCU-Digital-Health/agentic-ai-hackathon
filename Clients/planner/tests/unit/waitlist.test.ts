import { describe, expect, it } from 'vitest'
import type { WaitListItem } from '../../src/api/types'
import { byHighestPriorityFirst, sortWaitlist } from '../../src/lib/waitlist'

const patient = (id: number, priority: number): WaitListItem => ({
  id,
  patient_name: `Patient ${id}`,
  patient_id: id,
  priority,
})

describe('byHighestPriorityFirst', () => {
  it('puts priority 1 above priority 2, because priority is a rank', () => {
    expect(byHighestPriorityFirst(patient(1, 1), patient(2, 2))).toBeLessThan(0)
    expect(byHighestPriorityFirst(patient(1, 2), patient(2, 1))).toBeGreaterThan(0)
  })

  it('breaks ties by ascending id', () => {
    expect(byHighestPriorityFirst(patient(1, 3), patient(2, 3))).toBeLessThan(0)
    expect(byHighestPriorityFirst(patient(9, 3), patient(2, 3))).toBeGreaterThan(0)
  })
})

describe('sortWaitlist', () => {
  it('orders highest priority first', () => {
    const sorted = sortWaitlist([patient(1, 3), patient(2, 1), patient(3, 2)])

    expect(sorted.map((item) => item.id)).toEqual([2, 3, 1])
  })

  it('keeps insertion order within a priority', () => {
    const sorted = sortWaitlist([patient(7, 2), patient(3, 2), patient(5, 1)])

    expect(sorted.map((item) => item.id)).toEqual([5, 3, 7])
  })

  it('does not mutate its input', () => {
    const items = [patient(1, 3), patient(2, 1)]
    const snapshot = [...items]

    sortWaitlist(items)

    expect(items).toEqual(snapshot)
  })

  it('handles the empty and single-item cases', () => {
    expect(sortWaitlist([])).toEqual([])
    expect(sortWaitlist([patient(1, 4)]).map((item) => item.id)).toEqual([1])
  })
})
