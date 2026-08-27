import dayjs from 'dayjs'

/**
 * The single timezone boundary in the app.
 *
 * The backend serialises naive datetimes (no offset). We treat those as local
 * clinic time, which is what a scheduler means by "09:00". Every conversion
 * between an API string and a `Date` goes through here — `new Date(str)` is
 * never called anywhere else, so there is exactly one place to change if the
 * API starts sending offsets.
 */

/** Parse an API datetime string into a local-time `Date`. */
export const parseApiDate = (value: string): Date => dayjs(value).toDate()

/** Serialise a `Date` back into the naive local format the API expects. */
export const toApiDate = (value: Date): string =>
  dayjs(value).format('YYYY-MM-DDTHH:mm:ss')
