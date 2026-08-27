import { MantineProvider } from '@mantine/core'
import { DatesProvider } from '@mantine/dates'
import { Notifications } from '@mantine/notifications'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactNode } from 'react'
import type { Range } from '../../../src/lib/ranges'
import { ViewStateProvider } from '../../../src/state/ViewStateProvider'
import type { ViewMode } from '../../../src/state/useViewState'
import { theme } from '../../../src/styles/theme'

type Options = {
  initialRange?: Range
  initialMode?: ViewMode
  initialDate?: Date
}

/**
 * Mantine components need their provider, and anything touching the API needs a
 * QueryClient with retries off so a failure surfaces on the first attempt.
 */
export const renderWithProviders = (ui: ReactNode, options: Options = {}) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  })

  const result = render(
    // `env="test"` disables Mantine's transitions, which never settle under
    // jsdom and would otherwise leave portalled dropdowns at opacity 0.
    <MantineProvider theme={theme} forceColorScheme="light" env="test">
      <DatesProvider settings={{ firstDayOfWeek: 1 }}>
        <Notifications />
        <QueryClientProvider client={queryClient}>
          <ViewStateProvider {...options}>{ui}</ViewStateProvider>
        </QueryClientProvider>
      </DatesProvider>
    </MantineProvider>,
  )

  return { ...result, queryClient }
}
