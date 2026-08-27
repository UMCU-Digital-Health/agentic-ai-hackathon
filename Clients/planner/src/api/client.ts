import createClient from 'openapi-fetch'
import type { paths } from './schema'

/**
 * The generated paths already carry the `/api/v1` prefix, so the base is just
 * an origin. In dev that origin is the page's own, and the Vite proxy forwards
 * `/api` to the API on port 8080 — no CORS in the picture locally.
 * `VITE_API_BASE_URL` points a deployed build at a different origin.
 */
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  (typeof window === 'undefined' ? 'http://localhost' : window.location.origin)

export const api = createClient<paths>({
  baseUrl: API_BASE_URL,
  // openapi-fetch would otherwise capture `globalThis.fetch` at module load,
  // which is before MSW installs its interceptor in tests. Resolving it per
  // call costs nothing and keeps the mocked and real paths identical.
  fetch: (request) => globalThis.fetch(request),
})

/** Query keys, in one place so invalidation and reads can't drift apart. */
export const queryKeys = {
  calendarItems: ['calendar-items'] as const,
  waitlist: ['waitlist-items'] as const,
}
