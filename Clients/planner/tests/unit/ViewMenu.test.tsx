import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { Toolbar } from '../../src/components/toolbar/Toolbar'
import { renderWithProviders } from './helpers/renderWithProviders'

/** Mantine portals the dropdown, so items are queried on `screen`, not within a container. */
const openMenu = async (user: ReturnType<typeof userEvent.setup>, label: string) => {
  await user.click(screen.getByRole('button', { name: label }))
  await screen.findByRole('menuitemcheckbox', { name: 'List' })
}

describe('the view menu', () => {
  it('defaults to Week and Calendar', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Toolbar />, { initialDate: new Date(2026, 7, 27) })

    await openMenu(user, 'Week')

    expect(screen.getByRole('menuitemradio', { name: 'Week' })).toBeChecked()
    expect(screen.getByRole('menuitemcheckbox', { name: 'List' })).not.toBeChecked()
  })

  it('offers all five ranges plus the List toggle', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Toolbar />, { initialDate: new Date(2026, 7, 27) })

    await openMenu(user, 'Week')

    expect(screen.getAllByRole('menuitemradio').map((item) => item.textContent)).toEqual([
      'Day',
      'Three Day',
      'Working Week',
      'Week',
      'Month',
    ])
    expect(screen.getByRole('menuitemcheckbox', { name: 'List' })).toBeInTheDocument()
  })

  it('changing the range updates the toolbar label', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Toolbar />, { initialDate: new Date(2026, 7, 27) })

    expect(screen.getByTestId('range-label')).toHaveTextContent('24 August - 30 August 2026')

    await openMenu(user, 'Week')
    await user.click(screen.getByRole('menuitemradio', { name: 'Day' }))

    expect(screen.getByTestId('range-label')).toHaveTextContent('27 August 2026')
  })

  it('keeps the range ticked when List is switched on — the two are orthogonal', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Toolbar />, { initialDate: new Date(2026, 7, 27) })

    await openMenu(user, 'Week')
    await user.click(screen.getByRole('menuitemcheckbox', { name: 'List' }))

    expect(screen.getByRole('menuitemcheckbox', { name: 'List' })).toBeChecked()
    expect(screen.getByRole('menuitemradio', { name: 'Week' })).toBeChecked()
  })
})

describe('the toolbar navigation', () => {
  it('pages one span at a time and returns to today', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Toolbar />, { initialDate: new Date(2026, 7, 27) })

    await user.click(screen.getByRole('button', { name: 'Next period' }))
    expect(screen.getByTestId('range-label')).toHaveTextContent('31 August - 6 September 2026')

    await user.click(screen.getByRole('button', { name: 'Previous period' }))
    expect(screen.getByTestId('range-label')).toHaveTextContent('24 August - 30 August 2026')
  })
})
