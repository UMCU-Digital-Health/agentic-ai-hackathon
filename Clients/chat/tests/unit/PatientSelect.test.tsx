import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { PatientSelect } from '../../src/components/patient/PatientSelect'
import { renderWithProviders } from './helpers/renderWithProviders'

describe('PatientSelect', () => {
  it('lists patients as "name (#id)" and reports the chosen id', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    renderWithProviders(<PatientSelect value={null} onChange={onChange} />)

    const select = screen.getByRole('combobox', { name: 'Patient' })
    await vi.waitFor(() => expect(select).toBeEnabled())
    await user.click(select)

    expect(await screen.findByRole('option', { name: 'John Doe (#1)' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Youssef Bakkali (#6)' })).toBeInTheDocument()

    await user.click(screen.getByRole('option', { name: 'Jane Smith (#2)' }))
    expect(onChange).toHaveBeenCalledWith(2)
  })

  it('shows the selected patient', async () => {
    renderWithProviders(<PatientSelect value={3} onChange={() => {}} />)
    expect(await screen.findByDisplayValue('Pieter de Vries (#3)')).toBeInTheDocument()
  })

  it('keeps an unknown deep-linked id visible', async () => {
    renderWithProviders(<PatientSelect value={99} onChange={() => {}} />)
    expect(await screen.findByDisplayValue('Patient #99')).toBeInTheDocument()
  })
})
