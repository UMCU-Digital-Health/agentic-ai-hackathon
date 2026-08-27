import { MantineProvider } from '@mantine/core'
import { Notifications } from '@mantine/notifications'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactNode } from 'react'
import { theme } from '../../../src/styles/theme'

/**
 * Mantine components need their provider, and anything touching the API needs a
 * QueryClient with retries off so a failure surfaces on the first attempt.
 */
export const renderWithProviders = (ui: ReactNode) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  })

  const result = render(
    // `env="test"` disables Mantine's transitions, which never settle under
    // jsdom and would otherwise leave portalled dropdowns at opacity 0.
    <MantineProvider theme={theme} forceColorScheme="light" env="test">
      <Notifications />
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    </MantineProvider>,
  )

  return { ...result, queryClient }
}
