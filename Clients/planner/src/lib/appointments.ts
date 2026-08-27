import dayjs from 'dayjs'
import type { CalendarItem } from '../api/types'
import { APPOINTMENT_STATUS } from '../api/types'
import { parseApiDate } from '../api/dates'

/** A calendar item with its datetimes already parsed, for rendering and maths. */
export type Appointment = CalendarItem & { start: Date; end: Date }

export const toAppointment = (item: CalendarItem): Appointment => ({
  ...item,
  start: parseApiDate(item.start_time),
  end: parseApiDate(item.end_time),
})

export const isCanceled = (item: CalendarItem) =>
  item.status === APPOINTMENT_STATUS.canceled

/**
 * The appointments the planner shows and reasons about.
 *
 * Canceled ones are dropped entirely rather than styled as struck-through: a
 * canceled appointment is precisely a slot that has come free, so hiding it and
 * treating its time as bookable are the same statement. Everything downstream —
 * the grid, the list, collision checks, and the alternative-slot proposals —
 * reads this, so they cannot disagree about what is booked.
 */
export const activeAppointments = (items: readonly CalendarItem[]): CalendarItem[] =>
  items.filter((item) => !isCanceled(item))

/**
 * Appointments overlapping the span, earliest first.
 *
 * An appointment counts as in-range when any part of it falls inside the span,
 * so a consult running across midnight still shows on both days.
 */
export const appointmentsInRange = (
  items: readonly CalendarItem[],
  start: Date,
  end: Date,
): Appointment[] =>
  items
    .map(toAppointment)
    .filter(
      (appointment) =>
        appointment.start.getTime() <= end.getTime() &&
        appointment.end.getTime() >= start.getTime(),
    )
    .sort((a, b) => a.start.getTime() - b.start.getTime())

export type DayGroup = { key: string; date: Date; appointments: Appointment[] }

/**
 * Group appointments under the day they start on, for the list view's sticky
 * headers. Days with nothing on them are omitted rather than rendered empty.
 */
export const groupByDay = (appointments: readonly Appointment[]): DayGroup[] => {
  const groups = new Map<string, DayGroup>()
  for (const appointment of appointments) {
    const key = dayjs(appointment.start).format('YYYY-MM-DD')
    const group = groups.get(key)
    if (group) {
      group.appointments.push(appointment)
    } else {
      groups.set(key, {
        key,
        date: dayjs(appointment.start).startOf('day').toDate(),
        appointments: [appointment],
      })
    }
  }
  return [...groups.values()].sort((a, b) => a.date.getTime() - b.date.getTime())
}

/** `09:00` — the clock format used everywhere in the UI. */
export const formatTime = (value: Date) => dayjs(value).format('HH:mm')

/** `09:00 to 16:20`, as in the appointment popover. */
export const formatTimeRange = (start: Date, end: Date) =>
  `${formatTime(start)} to ${formatTime(end)}`

/** `Thursday, 27 August 2026`. */
export const formatFullDate = (value: Date) => dayjs(value).format('dddd, D MMMM YYYY')
