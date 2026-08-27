import type { components } from './schema'

export type CalendarItem = components['schemas']['CalendarItem']
export type CalendarItemInput = components['schemas']['CalendarItemInput']
export type WaitListItem = components['schemas']['WaitListItem']
export type WaitListItemInput = components['schemas']['WaitListItemInput']
export type Message = components['schemas']['Message']

/**
 * `erasableSyntaxOnly` rules out TS enums, so the appointment statuses are a
 * const object plus a derived union.
 */
export const APPOINTMENT_STATUS = {
  scheduled: 'scheduled',
  canceled: 'canceled',
} as const

export type AppointmentStatus =
  (typeof APPOINTMENT_STATUS)[keyof typeof APPOINTMENT_STATUS]
