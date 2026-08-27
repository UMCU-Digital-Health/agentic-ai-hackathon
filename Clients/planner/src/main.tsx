import { MantineProvider } from '@mantine/core'
import { DatesProvider } from '@mantine/dates'
import { Notifications } from '@mantine/notifications'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import dayjs from 'dayjs'
import isoWeek from 'dayjs/plugin/isoWeek'
import 'dayjs/locale/nl'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import '@mantine/core/styles.css'
import '@mantine/dates/styles.css'
import '@mantine/notifications/styles.css'
import './styles/tokens.css'
import './styles/fullcalendar-overrides.css'
import './index.css'

import { App } from './app/App'
import { ErrorBoundary } from './components/common/ErrorBoundary'
import { ViewStateProvider } from './state/ViewStateProvider'
import { theme } from './styles/theme'

// Monday-first weeks, registered once for the whole app.
dayjs.extend(isoWeek)

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
})

const start = async () => {
  if (import.meta.env.VITE_ENABLE_MSW === 'true') {
    const { worker } = await import('./mocks/browser')
    await worker.start({ onUnhandledRequest: 'bypass' })
  }

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <MantineProvider theme={theme} forceColorScheme="light">
        <DatesProvider settings={{ firstDayOfWeek: 1, locale: 'nl' }}>
          <Notifications position="bottom-right" />
          <QueryClientProvider client={queryClient}>
            <ErrorBoundary>
              <ViewStateProvider>
                <App />
              </ViewStateProvider>
            </ErrorBoundary>
          </QueryClientProvider>
        </DatesProvider>
      </MantineProvider>
    </StrictMode>,
  )
}

void start()
