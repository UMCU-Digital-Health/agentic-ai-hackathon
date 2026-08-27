import { HttpResponse, http } from 'msw'
import type { Message, MessageInput } from '../api/types'
import { makeMessages, makePatients } from './fixtures'

/**
 * One handler set, shared by Vitest (node) and Playwright (service worker).
 * State is mutable so a sent message shows up in the poll that follows it,
 * exactly as the real API behaves.
 */
let patients = makePatients()
let messages: Message[] = makeMessages()
let nextId = 100

export const resetMockData = () => {
  patients = makePatients()
  messages = makeMessages()
  nextId = 100
}

/** Append a message server-side, as the agent would; used by tests to exercise polling. */
export const pushMockMessage = (input: MessageInput): Message => {
  const created: Message = { ...input, id: (nextId += 1), timestamp: new Date().toISOString() }
  messages = [...messages, created]
  return created
}

export const handlers = [
  http.get('*/api/v1/patients', () => HttpResponse.json(patients)),

  http.get('*/api/v1/recent-messages/:patientId/:messageId', ({ params }) => {
    const patientId = Number(params.patientId)
    const messageId = Number(params.messageId)
    return HttpResponse.json(
      messages.filter((m) => m.patient_id === patientId && m.id > messageId),
    )
  }),

  http.get('*/api/v1/messages/:patientId', ({ params }) => {
    const patientId = Number(params.patientId)
    return HttpResponse.json(messages.filter((m) => m.patient_id === patientId))
  }),

  http.post('*/api/v1/messages', async ({ request }) => {
    const input = (await request.json()) as MessageInput
    return HttpResponse.json(pushMockMessage(input))
  }),
]
