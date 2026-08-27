import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import dayjs from 'dayjs'
import isoWeek from 'dayjs/plugin/isoWeek'
import { afterAll, afterEach, beforeAll, vi } from 'vitest'
import { resetMockData } from '../src/mocks/handlers'
import { server } from './unit/helpers/server'

dayjs.extend(isoWeek)

// Mantine reads both under jsdom and neither exists there.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver

window.scrollTo = vi.fn()

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))

afterEach(() => {
  cleanup()
  server.resetHandlers()
  resetMockData()
  window.localStorage.clear()
})

afterAll(() => server.close())
