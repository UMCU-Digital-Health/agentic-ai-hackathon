import type { Message, WaitListItem } from '../api/types'

/** The waitlist is where the chat's patient list comes from. */
export const makeWaitlist = (): WaitListItem[] => [
  { id: 1, patient_id: 1, patient_name: 'John Doe', priority: 1 },
  { id: 2, patient_id: 2, patient_name: 'Jane Smith', priority: 2 },
  { id: 3, patient_id: 3, patient_name: 'Pieter de Vries', priority: 3 },
  { id: 4, patient_id: 6, patient_name: 'Youssef Bakkali', priority: 4 },
]

const at = (minutesAgo: number) => new Date(Date.now() - minutesAgo * 60_000).toISOString()

/** Patients 1–3 have a conversation; patient 6 has none, so the -1 path stays covered. */
export const makeMessages = (): Message[] => [
  { id: 1, patient_id: 1, role: 'assistant', content: 'Hello John, a new timeslot is available.', timestamp: at(60) },
  { id: 2, patient_id: 1, role: 'user', content: 'Yes, I would like to reschedule.', timestamp: at(55) },
  { id: 3, patient_id: 2, role: 'assistant', content: 'Hello Jane, a new timeslot is available.', timestamp: at(40) },
  { id: 4, patient_id: 1, role: 'assistant', content: 'Wednesday 10:30 — shall I book it?', timestamp: at(30) },
  { id: 5, patient_id: 3, role: 'system', content: 'Conversation started.', timestamp: at(20) },
  { id: 6, patient_id: 3, role: 'assistant', content: 'Hello Pieter, a new timeslot is available.', timestamp: at(19) },
]
