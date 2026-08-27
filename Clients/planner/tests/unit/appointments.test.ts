import { describe, expect, it } from 'vitest'
import type { CalendarItem } from '../../src/api/types'
import {
  activeAppointments,
  appointmentsInRange,
  formatFullDate,
  formatTimeRange,
  groupByDay,
  isCanceled,
  toAppointment,
} from '../../src/lib/appointments'

const item = (
  id: number,
  start: string,
  end: string,
  status: CalendarItem['status'] = 'scheduled',
): CalendarItem => ({
  id,
  title: `Consult ${id}`,
  patient_id: id,
  patient_name: `Patient ${id}`,
  start_time: start,
  end_time: end,
  status,
})

describe('appointmentsInRange', () => {
  const week = { start: new Date(2026, 7, 24), end: new Date(2026, 7, 30, 23, 59, 59, 999) }

  it('keeps items inside the span and drops the rest', () => {
    const items = [
      item(1, '2026-08-25T09:00:00', '2026-08-25T09:30:00'),
      item(2, '2026-08-31T09:00:00', '2026-08-31T09:30:00'),
      item(3, '2026-08-23T09:00:00', '2026-08-23T09:30:00'),
    ]

    expect(appointmentsInRange(items, week.start, week.end).map((a) => a.id)).toEqual([1])
  })

  it('keeps an appointment that only partly overlaps the span', () => {
    const straddling = [item(1, '2026-08-23T22:00:00', '2026-08-24T01:00:00')]

    expect(appointmentsInRange(straddling, week.start, week.end)).toHaveLength(1)
  })

  it('returns them earliest first regardless of input order', () => {
    const items = [
      item(1, '2026-08-26T15:00:00', '2026-08-26T15:30:00'),
      item(2, '2026-08-24T09:00:00', '2026-08-24T09:30:00'),
      item(3, '2026-08-25T11:00:00', '2026-08-25T11:30:00'),
    ]

    expect(appointmentsInRange(items, week.start, week.end).map((a) => a.id)).toEqual([2, 3, 1])
  })

  it('returns nothing for an empty list', () => {
    expect(appointmentsInRange([], week.start, week.end)).toEqual([])
  })
})

describe('groupByDay', () => {
  it('groups appointments under the day they start on, in date order', () => {
    const appointments = [
      item(1, '2026-08-24T09:00:00', '2026-08-24T09:30:00'),
      item(2, '2026-08-24T11:00:00', '2026-08-24T11:30:00'),
      item(3, '2026-08-26T09:00:00', '2026-08-26T09:30:00'),
    ].map(toAppointment)

    const groups = groupByDay(appointments)

    expect(groups.map((group) => group.key)).toEqual(['2026-08-24', '2026-08-26'])
    expect(groups[0].appointments.map((a) => a.id)).toEqual([1, 2])
  })

  it('omits days with nothing on them', () => {
    expect(groupByDay([])).toEqual([])
  })
})

describe('activeAppointments', () => {
  it('drops canceled appointments — a canceled slot is a free slot', () => {
    const items = [
      item(1, '2026-08-24T09:00:00', '2026-08-24T09:30:00'),
      item(2, '2026-08-24T11:00:00', '2026-08-24T11:30:00', 'canceled'),
      item(3, '2026-08-25T09:00:00', '2026-08-25T09:30:00'),
    ]

    expect(activeAppointments(items).map((entry) => entry.id)).toEqual([1, 3])
  })

  it('does not mutate its input', () => {
    const items = [item(1, '2026-08-24T09:00:00', '2026-08-24T09:30:00', 'canceled')]

    activeAppointments(items)

    expect(items).toHaveLength(1)
  })

  it('handles the all-canceled and empty cases', () => {
    expect(activeAppointments([])).toEqual([])
    expect(
      activeAppointments([item(1, '2026-08-24T09:00:00', '2026-08-24T09:30:00', 'canceled')]),
    ).toEqual([])
  })
})

describe('formatting', () => {
  it('renders the popover time range', () => {
    expect(
      formatTimeRange(new Date(2026, 7, 27, 9, 0), new Date(2026, 7, 27, 16, 20)),
    ).toBe('09:00 to 16:20')
  })

  it('renders the popover date', () => {
    expect(formatFullDate(new Date(2026, 7, 27))).toBe('Thursday, 27 August 2026')
  })

  it('recognises a canceled appointment', () => {
    expect(isCanceled(item(1, '2026-08-27T09:00:00', '2026-08-27T09:30:00', 'canceled'))).toBe(true)
    expect(isCanceled(item(2, '2026-08-27T09:00:00', '2026-08-27T09:30:00'))).toBe(false)
  })
})
