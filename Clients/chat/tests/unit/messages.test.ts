import { describe, expect, it } from 'vitest'
import type { Message } from '../../src/api/types'
import { NO_MESSAGES, highestId, mergeMessages, patientLabel } from '../../src/lib/messages'

const msg = (id: number, content = `m${id}`): Message => ({
  id,
  patient_id: 1,
  role: 'user',
  content,
  timestamp: '2026-08-27T10:00:00',
})

describe('highestId', () => {
  it('is -1 when nothing is on screen', () => {
    expect(highestId([])).toBe(NO_MESSAGES)
    expect(NO_MESSAGES).toBe(-1)
  })

  it('finds the highest id regardless of order', () => {
    expect(highestId([msg(4), msg(9), msg(2)])).toBe(9)
  })
})

describe('mergeMessages', () => {
  it('dedupes by id, keeping the incoming copy', () => {
    const merged = mergeMessages([msg(1), msg(2, 'old')], [msg(2, 'new'), msg(3)])
    expect(merged.map((m) => m.id)).toEqual([1, 2, 3])
    expect(merged[1].content).toBe('new')
  })

  it('sorts by id', () => {
    expect(mergeMessages([msg(5)], [msg(1), msg(3)]).map((m) => m.id)).toEqual([1, 3, 5])
  })

  it('returns a new array and leaves the inputs untouched', () => {
    const existing = [msg(1)]
    const merged = mergeMessages(existing, [msg(2)])
    expect(existing).toHaveLength(1)
    expect(merged).toHaveLength(2)
  })
})

describe('patientLabel', () => {
  it('shows name and id', () => {
    expect(patientLabel({ id: 7, name: 'Anna Jansen' })).toBe('Anna Jansen (#7)')
  })
})
