import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { ChatScreen } from '../../src/components/chat/ChatScreen'
import { renderWithProviders } from './helpers/renderWithProviders'
import { server } from './helpers/server'

let posted: unknown[] = []

describe('ChatScreen', () => {
  beforeEach(() => {
    posted = []
    server.events.on('request:start', async ({ request }) => {
      if (request.method === 'POST') posted.push(await request.clone().json())
    })
  })
  afterEach(() => server.events.removeAllListeners())

  it('asks for a patient when none is selected', () => {
    renderWithProviders(<ChatScreen patientId={null} />)
    expect(screen.getByText(/select a patient/i)).toBeInTheDocument()
  })

  it('renders the conversation with roles', async () => {
    renderWithProviders(<ChatScreen patientId={1} />)
    const bubbles = await screen.findAllByTestId('message')
    expect(bubbles).toHaveLength(3)
    expect(bubbles[0]).toHaveAttribute('data-role', 'assistant')
    expect(bubbles[1]).toHaveAttribute('data-role', 'user')
    expect(within(bubbles[1]).getByText('Yes, I would like to reschedule.')).toBeInTheDocument()
  })

  it('shows an empty state for a patient without messages', async () => {
    renderWithProviders(<ChatScreen patientId={6} />)
    expect(await screen.findByText('No messages yet.')).toBeInTheDocument()
  })

  it('sends a message as the user and shows it exactly once', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ChatScreen patientId={2} />)
    await screen.findAllByTestId('message')

    await user.type(screen.getByRole('textbox', { name: 'Message' }), 'See you then{Enter}')

    expect(await screen.findByText('See you then')).toBeInTheDocument()
    expect(posted).toEqual([{ patient_id: 2, role: 'user', content: 'See you then' }])
    expect(screen.getByRole('textbox', { name: 'Message' })).toHaveValue('')

    // The next poll returns the same message; it must not render twice.
    await waitFor(() => expect(screen.getAllByTestId('message')).toHaveLength(2))
    expect(screen.getAllByText('See you then')).toHaveLength(1)
  })

  it('keeps the draft and warns when sending fails', async () => {
    const user = userEvent.setup()
    server.use(http.post('*/api/v1/messages', () => HttpResponse.error()))
    renderWithProviders(<ChatScreen patientId={2} />)
    await screen.findAllByTestId('message')

    await user.type(screen.getByRole('textbox', { name: 'Message' }), 'Hello{Enter}')

    expect(await screen.findByText('Message not sent')).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Message' })).toHaveValue('Hello')
  })

  it('shows an error when the first load fails', async () => {
    server.use(http.get('*/api/v1/recent-messages/:p/:m', () => HttpResponse.error()))
    renderWithProviders(<ChatScreen patientId={1} />)
    expect(await screen.findByText('Could not load messages')).toBeInTheDocument()
  })
})
