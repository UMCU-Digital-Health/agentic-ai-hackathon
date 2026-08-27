import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

/** Started from main.tsx when VITE_ENABLE_MSW is set — used by the e2e suite. */
export const worker = setupWorker(...handlers)
