import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import dayjs from 'dayjs'
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'
import { App } from '../../src/app/App'
import { renderWithProviders } from './helpers/renderWithProviders'
import { server } from './helpers/server'

/** The fixtures are anchored on the current Monday, so the app's default week shows them. */
const thisMonday = () => dayjs().startOf('isoWeek').toDate()

describe('the planner', () => {
  it('renders the shell', async () => {
    renderWithProviders(<App />, { initialMode: 'list', initialDate: thisMonday() })

    expect(screen.getByRole('heading', { name: 'NoShow Planner' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Waitlist' })).toBeInTheDocument()
  })

  it('lists this week\'s appointments in list view', async () => {
    renderWithProviders(<App />, { initialMode: 'list', initialDate: thisMonday() })

    expect(await screen.findByText('Intake - John Doe')).toBeInTheDocument()
    expect(screen.getByText('Controle - Jane Smith')).toBeInTheDocument()
    expect(screen.getByText('MRI-bespreking - Sanne Bakker')).toBeInTheDocument()
  })

  it('hides canceled appointments entirely', async () => {
    renderWithProviders(<App />, { initialMode: 'list', initialDate: thisMonday() })

    await screen.findByText('Intake - John Doe')
    // Fixture id 3 is canceled.
    expect(screen.queryByText('Nacontrole - Pieter de Vries')).not.toBeInTheDocument()
    expect(screen.queryByText(/canceled/i)).not.toBeInTheDocument()
  })

  it('shows the waitlist ordered by priority, highest first', async () => {
    renderWithProviders(<App />, { initialMode: 'list', initialDate: thisMonday() })

    await screen.findByText('Youssef Bakkali')
    const names = screen
      .getAllByText(/Youssef Bakkali|Anna Jansen|Lotte van Dijk/)
      .map((node) => node.textContent)

    expect(names).toEqual(['Youssef Bakkali', 'Anna Jansen', 'Lotte van Dijk'])
  })

  it('opens the details modal from a list row', async () => {
    const user = userEvent.setup()
    renderWithProviders(<App />, { initialMode: 'list', initialDate: thisMonday() })

    await user.click(await screen.findByText('Intake - John Doe'))

    const details = await screen.findByTestId('appointment-details')
    expect(within(details).getByText('John Doe')).toBeInTheDocument()
    expect(within(details).getByText('09:00 to 10:00')).toBeInTheDocument()
    expect(within(details).getByRole('button', { name: /edit event/i })).toBeInTheDocument()
  })

  it('deletes an appointment and removes it from the list', async () => {
    const user = userEvent.setup()
    renderWithProviders(<App />, { initialMode: 'list', initialDate: thisMonday() })

    await user.click(await screen.findByText('Intake - John Doe'))
    await user.click(await screen.findByRole('button', { name: /delete event/i }))

    await waitFor(() => {
      expect(screen.queryByText('Intake - John Doe')).not.toBeInTheDocument()
    })
    // Still gone after the refetch that follows the mutation.
    expect(screen.getByText('Controle - Jane Smith')).toBeInTheDocument()
  })

  it('offers alternative slots when rescheduling', async () => {
    const user = userEvent.setup()
    renderWithProviders(<App />, { initialMode: 'list', initialDate: thisMonday() })

    await user.click(await screen.findByText('Intake - John Doe'))
    await user.click(await screen.findByRole('button', { name: /edit event/i }))

    expect(await screen.findByText('Alternative times')).toBeInTheDocument()
    const options = screen.getAllByRole('radio')
    expect(options.length).toBeGreaterThan(0)

    await user.click(options[0])
    await user.click(screen.getByRole('button', { name: 'Reschedule' }))

    await waitFor(() => {
      expect(screen.queryByText('Alternative times')).not.toBeInTheDocument()
    })
  })

  it('shows an inline error rather than a blank pane when the fetch fails', async () => {
    server.use(
      http.get('*/api/v1/calendar-items', () =>
        HttpResponse.json({ detail: 'Boom' }, { status: 500 }),
      ),
    )
    renderWithProviders(<App />, { initialMode: 'list', initialDate: thisMonday() })

    expect(await screen.findByText('Could not load appointments')).toBeInTheDocument()
  })

  it('switches between calendar and list from the dropdown', async () => {
    const user = userEvent.setup()
    renderWithProviders(<App />, { initialDate: thisMonday() })

    expect(await screen.findByTestId('calendar-view')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Week' }))
    await user.click(await screen.findByRole('menuitemcheckbox', { name: 'List' }))

    expect(await screen.findByTestId('list-view')).toBeInTheDocument()
    expect(screen.queryByTestId('calendar-view')).not.toBeInTheDocument()
  })
})
