import dayjs from 'dayjs'
import type { Appointment } from './appointments'

/** Clinic working hours, in local time. Slots are only ever proposed inside these. */
export const WORKING_HOURS = { startHour: 8, endHour: 18 } as const

/** Candidate starts sit on a 30-minute grid, matching the calendar's slots. */
const GRID_MINUTES = 30

const isWorkingDay = (day: dayjs.Dayjs) => day.isoWeekday() <= 5

/**
 * Does `[start, end)` collide with an existing appointment?
 *
 * `ignoreId` excludes the appointment being moved, so dragging an event a few
 * minutes sideways doesn't count as colliding with itself. Touching edges
 * (one ends exactly where the next begins) is not an overlap.
 */
export const overlapsExisting = (
  appointments: readonly Appointment[],
  start: Date,
  end: Date,
  ignoreId?: number,
): boolean =>
  appointments.some(
    (appointment) =>
      appointment.id !== ignoreId &&
      start.getTime() < appointment.end.getTime() &&
      end.getTime() > appointment.start.getTime(),
  )

export type ProposedSlot = { start: Date; end: Date }

type SuggestOptions = {
  /** Slots are searched forward from here; defaults to the appointment's own start. */
  from?: Date
  /** How many days ahead to search. */
  horizonDays?: number
  /** How many proposals to return. */
  count?: number
}

/**
 * Propose alternative times for an appointment.
 *
 * The API has no "alternative slots" endpoint (that is the agent's job later),
 * so this computes them client-side: same duration, inside working hours on a
 * weekday, not overlapping anything already booked, and never the slot the
 * appointment already occupies. Nearest-first, because the patient who has to
 * be called about it cares most about how far the appointment moves.
 */
export const suggestSlots = (
  appointment: Appointment,
  appointments: readonly Appointment[],
  { from, horizonDays = 14, count = 5 }: SuggestOptions = {},
): ProposedSlot[] => {
  const durationMs = appointment.end.getTime() - appointment.start.getTime()
  if (durationMs <= 0) return []

  const searchFrom = dayjs(from ?? appointment.start).startOf('day')
  const proposals: ProposedSlot[] = []

  for (let dayOffset = 0; dayOffset < horizonDays; dayOffset += 1) {
    const day = searchFrom.add(dayOffset, 'day')
    if (!isWorkingDay(day)) continue

    const dayEnd = day.hour(WORKING_HOURS.endHour).startOf('hour')
    let candidate = day.hour(WORKING_HOURS.startHour).startOf('hour')

    while (candidate.valueOf() + durationMs <= dayEnd.valueOf()) {
      const start = candidate.toDate()
      const end = new Date(start.getTime() + durationMs)
      const isCurrentSlot = start.getTime() === appointment.start.getTime()
      if (!isCurrentSlot && !overlapsExisting(appointments, start, end, appointment.id)) {
        proposals.push({ start, end })
      }
      candidate = candidate.add(GRID_MINUTES, 'minute')
    }
  }

  return proposals
    .sort(
      (a, b) =>
        Math.abs(a.start.getTime() - appointment.start.getTime()) -
        Math.abs(b.start.getTime() - appointment.start.getTime()),
    )
    .slice(0, count)
}
