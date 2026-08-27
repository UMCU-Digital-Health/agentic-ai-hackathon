import { describe, expect, it } from 'vitest'
import { getRange, step } from '../../src/lib/ranges'

const date = (iso: string) => new Date(iso)

/** Local-time YYYY-MM-DD HH:mm, so assertions read as clinic time. */
const stamp = (value: Date) =>
  `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(
    value.getDate(),
  ).padStart(2, '0')} ${String(value.getHours()).padStart(2, '0')}:${String(
    value.getMinutes(),
  ).padStart(2, '0')}`

describe('getRange', () => {
  it('covers a single day for the day range', () => {
    const { start, end, label, fcView } = getRange('day', date('2026-08-27T13:20:00'))

    expect(stamp(start)).toBe('2026-08-27 00:00')
    expect(stamp(end)).toBe('2026-08-27 23:59')
    expect(label).toBe('27 August 2026')
    expect(fcView).toBe('timeGridDay')
  })

  it('starts the three-day range at the anchor rather than a week boundary', () => {
    const { start, end, label } = getRange('threeDay', date('2026-08-27T09:00:00'))

    expect(stamp(start)).toBe('2026-08-27 00:00')
    expect(stamp(end)).toBe('2026-08-29 23:59')
    expect(label).toBe('27 August - 29 August 2026')
  })

  it('runs Monday to Friday for the working week', () => {
    const { start, end } = getRange('workWeek', date('2026-08-27T09:00:00'))

    expect(stamp(start)).toBe('2026-08-24 00:00')
    expect(stamp(end)).toBe('2026-08-28 23:59')
  })

  it('runs Monday to Sunday for the week', () => {
    const { start, end, label } = getRange('week', date('2026-08-27T09:00:00'))

    expect(stamp(start)).toBe('2026-08-24 00:00')
    expect(stamp(end)).toBe('2026-08-30 23:59')
    expect(label).toBe('24 August - 30 August 2026')
  })

  it('anchors the week on Monday when the anchor is itself a Sunday', () => {
    const { start, end } = getRange('week', date('2026-08-30T22:00:00'))

    expect(stamp(start)).toBe('2026-08-24 00:00')
    expect(stamp(end)).toBe('2026-08-30 23:59')
  })

  it('covers the whole month for the month range', () => {
    const { start, end, label, fcView } = getRange('month', date('2026-02-14T09:00:00'))

    expect(stamp(start)).toBe('2026-02-01 00:00')
    expect(stamp(end)).toBe('2026-02-28 23:59')
    expect(label).toBe('February 2026')
    expect(fcView).toBe('dayGridMonth')
  })

  it('spans two months when a week straddles the boundary', () => {
    const { start, end, label } = getRange('week', date('2026-09-01T09:00:00'))

    expect(stamp(start)).toBe('2026-08-31 00:00')
    expect(stamp(end)).toBe('2026-09-06 23:59')
    expect(label).toBe('31 August - 6 September 2026')
  })

  it('spells out both years when a week straddles new year', () => {
    const { label } = getRange('week', date('2025-12-31T09:00:00'))

    expect(label).toBe('29 December 2025 - 4 January 2026')
  })

  it('keeps midnight-to-midnight day boundaries across a DST transition', () => {
    // The Netherlands moves to summer time on 29 March 2026.
    const { start, end } = getRange('day', date('2026-03-29T12:00:00'))

    expect(stamp(start)).toBe('2026-03-29 00:00')
    expect(stamp(end)).toBe('2026-03-29 23:59')
  })
})

describe('step', () => {
  it('moves a day at a time for the day range', () => {
    expect(stamp(step('day', date('2026-08-27T09:00:00'), 1))).toBe('2026-08-28 09:00')
    expect(stamp(step('day', date('2026-08-27T09:00:00'), -1))).toBe('2026-08-26 09:00')
  })

  it('moves three days for the three-day range, so pages never overlap', () => {
    expect(stamp(step('threeDay', date('2026-08-27T09:00:00'), 1))).toBe('2026-08-30 09:00')
  })

  it('moves a week for both week ranges', () => {
    expect(stamp(step('week', date('2026-08-27T09:00:00'), 1))).toBe('2026-09-03 09:00')
    expect(stamp(step('workWeek', date('2026-08-27T09:00:00'), -1))).toBe('2026-08-20 09:00')
  })

  it('snaps to the first of the month when paging months', () => {
    expect(stamp(step('month', date('2026-01-31T09:00:00'), 1))).toBe('2026-02-01 00:00')
  })

  it('crosses a year boundary', () => {
    expect(stamp(step('month', date('2026-12-15T09:00:00'), 1))).toBe('2027-01-01 00:00')
  })
})
