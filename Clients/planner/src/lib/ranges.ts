import dayjs from 'dayjs'
import type { Dayjs } from 'dayjs'

/** The five spans the filter dropdown offers. */
export const RANGES = ['day', 'threeDay', 'workWeek', 'week', 'month'] as const
export type Range = (typeof RANGES)[number]

export const RANGE_LABELS: Record<Range, string> = {
  day: 'Day',
  threeDay: 'Three Day',
  workWeek: 'Working Week',
  week: 'Week',
  month: 'Month',
}

/** Which FullCalendar view renders each range. */
export const FC_VIEWS: Record<Range, string> = {
  day: 'timeGridDay',
  threeDay: 'timeGridThreeDay',
  workWeek: 'timeGridWorkWeek',
  week: 'timeGridWeek',
  month: 'dayGridMonth',
}

export type ResolvedRange = {
  /** First instant of the span, inclusive. */
  start: Date
  /** Last instant of the span, inclusive (end of the final day). */
  end: Date
  /** Human label for the toolbar, e.g. "24 August - 30 August 2026". */
  label: string
  fcView: string
}

const startOfSpan = (range: Range, anchor: Dayjs): Dayjs => {
  switch (range) {
    case 'day':
    case 'threeDay':
      return anchor.startOf('day')
    case 'workWeek':
    case 'week':
      return anchor.startOf('isoWeek')
    case 'month':
      return anchor.startOf('month')
  }
}

const endOfSpan = (range: Range, start: Dayjs): Dayjs => {
  switch (range) {
    case 'day':
      return start.endOf('day')
    case 'threeDay':
      return start.add(2, 'day').endOf('day')
    case 'workWeek':
      return start.add(4, 'day').endOf('day')
    case 'week':
      return start.add(6, 'day').endOf('day')
    case 'month':
      return start.endOf('month')
  }
}

const formatLabel = (range: Range, start: Dayjs, end: Dayjs): string => {
  if (range === 'month') return start.format('MMMM YYYY')
  if (start.isSame(end, 'day')) return start.format('D MMMM YYYY')
  if (start.isSame(end, 'year')) {
    return `${start.format('D MMMM')} - ${end.format('D MMMM YYYY')}`
  }
  return `${start.format('D MMMM YYYY')} - ${end.format('D MMMM YYYY')}`
}

/**
 * Resolve a range plus an anchor date into the span the views render.
 *
 * Weeks are Monday-first (ISO), which is what `dayjs/plugin/isoWeek` gives us
 * and what the clinic expects. `threeDay` starts *at* the anchor rather than
 * snapping to a week boundary, matching Outlook's behaviour.
 */
export const getRange = (range: Range, anchor: Date): ResolvedRange => {
  const start = startOfSpan(range, dayjs(anchor))
  const end = endOfSpan(range, start)
  return {
    start: start.toDate(),
    end: end.toDate(),
    label: formatLabel(range, start, end),
    fcView: FC_VIEWS[range],
  }
}

/**
 * Move the anchor one span forward (`delta: 1`) or back (`delta: -1`).
 *
 * The step matches the span so paging never skips or repeats days: a day at a
 * time, three days for the three-day view, a week for both week views, a month
 * for the month view.
 */
export const step = (range: Range, anchor: Date, delta: number): Date => {
  const current = dayjs(anchor)
  switch (range) {
    case 'day':
      return current.add(delta, 'day').toDate()
    case 'threeDay':
      return current.add(delta * 3, 'day').toDate()
    case 'workWeek':
    case 'week':
      return current.add(delta, 'week').toDate()
    case 'month':
      return current.add(delta, 'month').startOf('month').toDate()
  }
}
