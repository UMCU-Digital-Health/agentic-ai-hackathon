import type { components } from './schema'

export type Message = components['schemas']['Message']
export type MessageInput = components['schemas']['MessageInput']
export type Patient = components['schemas']['Patient']

/**
 * `erasableSyntaxOnly` rules out TS enums, so roles are a const object plus a
 * derived union.
 */
export const MESSAGE_ROLE = {
  system: 'system',
  user: 'user',
  assistant: 'assistant',
} as const

export type MessageRole = (typeof MESSAGE_ROLE)[keyof typeof MESSAGE_ROLE]

/**
 * The role attached to messages typed in this client. The API's roles are
 * chat-model-centric (the patient is the `user`), so this is a single constant
 * to flip if the clinician should send as something else.
 */
export const SENT_ROLE: MessageRole = MESSAGE_ROLE.user
