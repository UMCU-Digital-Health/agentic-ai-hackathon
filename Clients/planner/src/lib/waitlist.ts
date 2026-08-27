import type { WaitListItem } from '../api/types'

/**
 * Highest priority first. `priority` is a rank, not a magnitude: 1 is the most
 * urgent patient, so the numeric sort is ascending. The function name states
 * the intent because the mechanics read backwards at a glance.
 *
 * Ties break by `id` ascending so equal priorities fall back to insertion order
 * and the list never reshuffles between renders.
 */
export const byHighestPriorityFirst = (a: WaitListItem, b: WaitListItem) =>
  a.priority - b.priority || a.id - b.id

/** Sort a copy — the query cache's array is never mutated. */
export const sortWaitlist = (items: readonly WaitListItem[]) =>
  [...items].sort(byHighestPriorityFirst)
