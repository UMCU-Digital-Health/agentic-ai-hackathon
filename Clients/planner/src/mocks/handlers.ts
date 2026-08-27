import { HttpResponse, http } from 'msw'
import type { CalendarItem, CalendarItemInput, WaitListItem, WaitListItemInput } from '../api/types'
import { makeCalendarItems, makeWaitlistItems } from './fixtures'

/**
 * One handler set, shared by Vitest (node) and Playwright (service worker).
 * State is mutable so a delete stays deleted across the refetch that follows it,
 * exactly as the real API behaves.
 */
let calendarItems: CalendarItem[] = makeCalendarItems()
let waitlistItems: WaitListItem[] = makeWaitlistItems()
let nextId = 100

export const resetMockData = () => {
  calendarItems = makeCalendarItems()
  waitlistItems = makeWaitlistItems()
  nextId = 100
}

const patientNameFor = (patientId: number) =>
  [...calendarItems, ...waitlistItems].find((item) => item.patient_id === patientId)
    ?.patient_name ?? `Patient ${patientId}`

export const handlers = [
  http.get('*/api/v1/calendar-items', () => HttpResponse.json(calendarItems)),

  http.post('*/api/v1/calendar-items', async ({ request }) => {
    const input = (await request.json()) as CalendarItemInput
    const created: CalendarItem = {
      ...input,
      id: (nextId += 1),
      patient_name: patientNameFor(input.patient_id),
    }
    calendarItems = [...calendarItems, created]
    return HttpResponse.json(created)
  }),

  http.put('*/api/v1/calendar-items/:id', async ({ params, request }) => {
    const id = Number(params.id)
    const input = (await request.json()) as CalendarItemInput
    const existing = calendarItems.find((item) => item.id === id)
    if (!existing) return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    const updated: CalendarItem = { ...input, id, patient_name: existing.patient_name }
    calendarItems = calendarItems.map((item) => (item.id === id ? updated : item))
    return HttpResponse.json(updated)
  }),

  http.delete('*/api/v1/calendar-items/:id', ({ params }) => {
    const id = Number(params.id)
    if (!calendarItems.some((item) => item.id === id)) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    }
    calendarItems = calendarItems.filter((item) => item.id !== id)
    return HttpResponse.json({ message: `Calendar item '${id}' deleted successfully.` })
  }),

  http.get('*/api/v1/waitlist-items', () => HttpResponse.json(waitlistItems)),

  http.post('*/api/v1/waitlist-items', async ({ request }) => {
    const input = (await request.json()) as WaitListItemInput
    const created: WaitListItem = {
      ...input,
      id: (nextId += 1),
      priority: Math.max(0, ...waitlistItems.map((item) => item.priority)) + 1,
    }
    waitlistItems = [...waitlistItems, created]
    return HttpResponse.json(created)
  }),

  http.delete('*/api/v1/waitlist-items/:id', ({ params }) => {
    const id = Number(params.id)
    waitlistItems = waitlistItems.filter((item) => item.id !== id)
    return HttpResponse.json({ message: `Waitlist item '${id}' deleted successfully.` })
  }),
]
