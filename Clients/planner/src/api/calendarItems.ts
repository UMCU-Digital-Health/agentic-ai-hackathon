import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { CalendarItem } from './types'
import { api, queryKeys, REFRESH_INTERVAL_MS } from './client'
import { toApiDate } from './dates'

const unwrap = <T,>(result: { data?: T; error?: unknown }): T => {
  if (result.error !== undefined || result.data === undefined) {
    throw new Error(describeError(result.error))
  }
  return result.data
}

const describeError = (error: unknown): string => {
  if (typeof error === 'object' && error !== null && 'detail' in error) {
    const { detail } = error as { detail: unknown }
    if (typeof detail === 'string') return detail
  }
  return 'The request failed. Is the API running on port 8080?'
}

export const useCalendarItems = () =>
  useQuery({
    queryKey: queryKeys.calendarItems,
    queryFn: async () => unwrap(await api.GET('/api/v1/calendar-items')),
    refetchInterval: REFRESH_INTERVAL_MS,
  })

type Reschedule = { item: CalendarItem; start: Date; end: Date }

/**
 * Move an appointment to a new position in time.
 *
 * `PUT` is a full replace, so a partial body would silently blank fields: the
 * new times are always spread over the *cached* item rather than sent alone.
 * Used by both drag-to-move and the Edit modal's alternative-slot picker.
 */
export const useMoveCalendarItem = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ item, start, end }: Reschedule) =>
      unwrap(
        await api.PUT('/api/v1/calendar-items/{item_id}', {
          params: { path: { item_id: item.id } },
          body: {
            title: item.title,
            patient_id: item.patient_id,
            status: item.status,
            start_time: toApiDate(start),
            end_time: toApiDate(end),
          },
        }),
      ),
    onMutate: async ({ item, start, end }: Reschedule) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.calendarItems })
      const previous = queryClient.getQueryData<CalendarItem[]>(queryKeys.calendarItems)
      queryClient.setQueryData<CalendarItem[]>(queryKeys.calendarItems, (items) =>
        items?.map((candidate) =>
          candidate.id === item.id
            ? { ...candidate, start_time: toApiDate(start), end_time: toApiDate(end) }
            : candidate,
        ),
      )
      return { previous }
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.calendarItems, context.previous)
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.calendarItems })
    },
  })
}

/** Delete an appointment, removing it from the grid before the round-trip. */
export const useDeleteCalendarItem = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: number) =>
      unwrap(
        await api.DELETE('/api/v1/calendar-items/{item_id}', {
          params: { path: { item_id: id } },
        }),
      ),
    onMutate: async (id: number) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.calendarItems })
      const previous = queryClient.getQueryData<CalendarItem[]>(queryKeys.calendarItems)
      queryClient.setQueryData<CalendarItem[]>(queryKeys.calendarItems, (items) =>
        items?.filter((candidate) => candidate.id !== id),
      )
      return { previous }
    },
    onError: (_error, _id, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.calendarItems, context.previous)
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.calendarItems })
    },
  })
}
