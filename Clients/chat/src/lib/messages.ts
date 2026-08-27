import type { Message, Patient } from '../api/types'

/** The cursor sent to the API when nothing is on screen yet. */
export const NO_MESSAGES = -1

/** Highest message id in `messages`, or `NO_MESSAGES` when the list is empty. */
export const highestId = (messages: readonly Message[]): number =>
  messages.reduce((max, message) => Math.max(max, message.id), NO_MESSAGES)

/**
 * Combine what is on screen with what a poll (or a send) returned. Deduped by
 * id — a message echoed back from a send and then delivered by the next poll
 * must never render twice — and sorted by id, which is the server's order.
 */
export const mergeMessages = (
  existing: readonly Message[],
  incoming: readonly Message[],
): Message[] => {
  const byId = new Map<number, Message>()
  for (const message of [...existing, ...incoming]) byId.set(message.id, message)
  return [...byId.values()].sort((a, b) => a.id - b.id)
}

/** The dropdown label: name plus id, so patients with the same name stay apart. */
export const patientLabel = (patient: Patient): string => `${patient.name} (#${patient.id})`
