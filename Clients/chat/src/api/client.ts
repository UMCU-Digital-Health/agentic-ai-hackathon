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
  // Resolve fetch per call so MSW's interceptor (installed after module load
  // in tests) is picked up, and the mocked and real paths stay identical.
  fetch: (request) => globalThis.fetch(request),
})

/** Query keys, in one place so invalidation and reads can't drift apart. */
export const queryKeys = {
  patients: ['patients'] as const,
  messages: (patientId: number | null) => ['messages', patientId] as const,
}

export const unwrap = <T,>(result: { data?: T; error?: unknown }): T => {
  if (result.error !== undefined || result.data === undefined) {
    throw new Error('The request failed. Is the API running on port 8080?')
  }
  return result.data
}
