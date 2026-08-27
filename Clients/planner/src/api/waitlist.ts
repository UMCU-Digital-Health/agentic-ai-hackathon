import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { CalendarItem, WaitListItem } from './types'
import { APPOINTMENT_STATUS } from './types'
import { api, queryKeys } from './client'
import { toApiDate } from './dates'

const unwrap = <T,>(result: { data?: T; error?: unknown }): T => {
  if (result.error !== undefined || result.data === undefined) {
    throw new Error('The request failed. Is the API running on port 8080?')
  }
  return result.data
}

export const useWaitlist = () =>
  useQuery({
    queryKey: queryKeys.waitlist,
    queryFn: async () => unwrap(await api.GET('/api/v1/waitlist-items')),
  })

type Scheduling = { patient: WaitListItem; start: Date; end: Date }

/**
 * Turn a waiting patient into an appointment: create the calendar item, then
 * drop them from the waitlist. The create runs first so a failure leaves the
 * patient waiting rather than silently disappearing.
 */
export const useScheduleWaitlistItem = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ patient, start, end }: Scheduling): Promise<CalendarItem> => {
      const created = unwrap(
        await api.POST('/api/v1/calendar-items', {
          body: {
            title: `Afspraak - ${patient.patient_name}`,
            patient_id: patient.patient_id,
            status: APPOINTMENT_STATUS.scheduled,
            start_time: toApiDate(start),
            end_time: toApiDate(end),
          },
        }),
      )
      unwrap(
        await api.DELETE('/api/v1/waitlist-items/{item_id}', {
          params: { path: { item_id: patient.id } },
        }),
      )
      return created
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.calendarItems })
      void queryClient.invalidateQueries({ queryKey: queryKeys.waitlist })
    },
  })
}
