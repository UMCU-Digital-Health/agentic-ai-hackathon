import { setupWorker } from 'msw/browser'
import { handlers, pushMockMessage } from './handlers'

/** Started from main.tsx when VITE_ENABLE_MSW is set — used by the e2e suite. */
export const worker = setupWorker(...handlers)

declare global {
  interface Window {
    /** Test hook: simulate the agent replying so the e2e suite can watch polling pick it up. */
    __pushMessage?: typeof pushMockMessage
  }
}

window.__pushMessage = pushMockMessage
