import { describe, expect, it } from 'vitest'
import type { Appointment } from '../../src/lib/appointments'
import { overlapsExisting, suggestSlots, WORKING_HOURS } from '../../src/lib/slots'

const appointment = (
  id: number,
  startIso: string,
  minutes: number,
): Appointment => {
  const start = new Date(startIso)
  const end = new Date(start.getTime() + minutes * 60_000)
  return {
    id,
    title: `Consult ${id}`,
    patient_id: id,
    patient_name: `Patient ${id}`,
    start_time: startIso,
    end_time: end.toISOString(),
    status: 'scheduled',
    start,
    end,
  }
}

describe('overlapsExisting', () => {
  const booked = [appointment(1, '2026-08-27T09:00:00', 60)]

  it('reports an overlap when the spans intersect', () => {
    expect(
      overlapsExisting(booked, new Date('2026-08-27T09:30:00'), new Date('2026-08-27T10:30:00')),
    ).toBe(true)
  })

  it('does not treat touching edges as an overlap', () => {
    expect(
      overlapsExisting(booked, new Date('2026-08-27T10:00:00'), new Date('2026-08-27T10:30:00')),
    ).toBe(false)
    expect(
      overlapsExisting(booked, new Date('2026-08-27T08:30:00'), new Date('2026-08-27T09:00:00')),
    ).toBe(false)
  })

  it('ignores the appointment being moved, so it cannot collide with itself', () => {
    expect(
      overlapsExisting(
        booked,
        new Date('2026-08-27T09:15:00'),
        new Date('2026-08-27T10:15:00'),
        1,
      ),
    ).toBe(false)
  })
})

describe('suggestSlots', () => {
  const target = appointment(1, '2026-08-27T09:00:00', 30) // Thursday

  it('preserves the appointment duration', () => {
    const ninetyMinutes = appointment(1, '2026-08-27T09:00:00', 90)

    for (const slot of suggestSlots(ninetyMinutes, [ninetyMinutes])) {
      expect(slot.end.getTime() - slot.start.getTime()).toBe(90 * 60_000)
    }
  })

  it('stays inside working hours', () => {
    for (const slot of suggestSlots(target, [target])) {
      expect(slot.start.getHours()).toBeGreaterThanOrEqual(WORKING_HOURS.startHour)
      expect(slot.end.getHours()).toBeLessThanOrEqual(WORKING_HOURS.endHour)
    }
  })

  it('never proposes a weekend', () => {
    const friday = appointment(1, '2026-08-28T16:00:00', 30)

    for (const slot of suggestSlots(friday, [friday])) {
      expect(slot.start.getDay()).not.toBe(0)
      expect(slot.start.getDay()).not.toBe(6)
    }
  })

  it('never proposes a slot that overlaps an existing appointment', () => {
    const booked = [
      target,
      appointment(2, '2026-08-27T08:00:00', 240),
      appointment(3, '2026-08-27T13:00:00', 300),
    ]

    for (const slot of suggestSlots(target, booked)) {
      expect(overlapsExisting(booked, slot.start, slot.end, target.id)).toBe(false)
    }
  })

  it('never proposes the slot the appointment already occupies', () => {
    const starts = suggestSlots(target, [target]).map((slot) => slot.start.getTime())

    expect(starts).not.toContain(target.start.getTime())
  })

  it('orders proposals nearest to the original time first', () => {
    const slots = suggestSlots(target, [target])
    const distances = slots.map((slot) =>
      Math.abs(slot.start.getTime() - target.start.getTime()),
    )

    expect(distances).toEqual([...distances].sort((a, b) => a - b))
    expect(slots).toHaveLength(5)
  })

  it('returns nothing for a zero-length appointment', () => {
    const zeroLength = appointment(1, '2026-08-27T09:00:00', 0)

    expect(suggestSlots(zeroLength, [])).toEqual([])
  })

  it('returns nothing when every working hour in the horizon is booked', () => {
    const blocked = [target]
    for (let day = 0; day < 20; day += 1) {
      const start = new Date('2026-08-24T00:00:00')
      start.setDate(start.getDate() + day)
      blocked.push(appointment(100 + day, start.toISOString(), 24 * 60))
    }

    expect(suggestSlots(target, blocked, { horizonDays: 14 })).toEqual([])
  })
})
