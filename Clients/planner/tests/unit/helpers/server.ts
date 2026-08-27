import { setupServer } from 'msw/node'
import { handlers } from '../../../src/mocks/handlers'

/** The Vitest half of the shared handler set; Playwright runs the same set in a worker. */
export const server = setupServer(...handlers)
