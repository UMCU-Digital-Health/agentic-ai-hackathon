import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useMessages } from '../../src/api/messages'
import { pushMockMessage } from '../../src/mocks/handlers'
import { server } from './helpers/server'

const recentPaths = () => requested.filter((url) => url.includes('/recent-messages/'))
let requested: string[] = []

const makeWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
  return { wrapper, queryClient }
}

describe('useMessages', () => {
  beforeEach(() => {
    requested = []
    server.events.on('request:start', ({ request }) => {
      requested.push(new URL(request.url).pathname)
    })
  })
  afterEach(() => {
    server.events.removeAllListeners()
    vi.useRealTimers()
  })

  it('does nothing without a patient', () => {
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useMessages(null), { wrapper })
    expect(result.current.fetchStatus).toBe('idle')
    expect(requested).toHaveLength(0)
  })

  it('asks from -1 first and from the highest id on screen afterwards', async () => {
    const { wrapper, queryClient } = makeWrapper()
    const { result } = renderHook(() => useMessages(1), { wrapper })

    await waitFor(() => expect(result.current.data?.map((m) => m.id)).toEqual([1, 2, 4]))
    expect(recentPaths()).toEqual(['/api/v1/recent-messages/1/-1'])

    pushMockMessage({ patient_id: 1, role: 'assistant', content: 'Booked.' })
    await queryClient.refetchQueries()

    await waitFor(() => expect(result.current.data?.map((m) => m.id)).toEqual([1, 2, 4, 101]))
    expect(recentPaths()).toEqual([
      '/api/v1/recent-messages/1/-1',
      '/api/v1/recent-messages/1/4',
    ])
  })

  it('polls on an interval', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useMessages(2), { wrapper })
    await waitFor(() => expect(result.current.data).toHaveLength(1))

    pushMockMessage({ patient_id: 2, role: 'assistant', content: 'Still there?' })
    await vi.advanceTimersByTimeAsync(2_100)

    await waitFor(() => expect(result.current.data).toHaveLength(2))
    expect(recentPaths().at(-1)).toBe('/api/v1/recent-messages/2/3')
  })

  it('starts a new patient from -1 while remembering the previous cursor', async () => {
    const { wrapper } = makeWrapper()
    const { result, rerender } = renderHook(({ id }) => useMessages(id), {
      wrapper,
      initialProps: { id: 1 },
    })
    await waitFor(() => expect(result.current.data).toHaveLength(3))

    rerender({ id: 6 })
    await waitFor(() => expect(result.current.data).toEqual([]))
    expect(recentPaths().at(-1)).toBe('/api/v1/recent-messages/6/-1')

    rerender({ id: 1 })
    await waitFor(() => expect(recentPaths().at(-1)).toBe('/api/v1/recent-messages/1/4'))
  })
})
