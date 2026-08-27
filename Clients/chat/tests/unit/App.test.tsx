import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { App } from '../../src/app/App'
import { renderWithProviders } from './helpers/renderWithProviders'

describe('the chat app', () => {
  it('renders the shell with the patient selector', async () => {
    renderWithProviders(<App />)
    expect(screen.getByRole('heading', { name: 'NoShow Chat' })).toBeInTheDocument()
    expect(screen.getByTestId('patient-select')).toBeInTheDocument()
    expect(screen.getByText(/select a patient/i)).toBeInTheDocument()
  })

  it('opens a deep-linked conversation', async () => {
    window.history.replaceState(null, '', '/?patientId=1')
    renderWithProviders(<App />)
    expect(await screen.findByText('Wednesday 10:30 — shall I book it?')).toBeInTheDocument()
    expect(await screen.findByDisplayValue('John Doe (#1)')).toBeInTheDocument()
  })

  it('switches patient from the dropdown and updates the URL', async () => {
    const user = userEvent.setup()
    renderWithProviders(<App />)
    const select = screen.getByRole('combobox', { name: 'Patient' })
    await vi.waitFor(() => expect(select).toBeEnabled())
    await user.click(select)
    await user.click(await screen.findByRole('option', { name: 'Pieter de Vries (#3)' }))

    expect(window.location.search).toBe('?patientId=3')
    expect(await screen.findByText('Hello Pieter, a new timeslot is available.')).toBeInTheDocument()
  })
})
