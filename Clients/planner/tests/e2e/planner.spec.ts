import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

/**
 * The app runs against the MSW handlers in `src/mocks`, whose fixtures are
 * anchored on the current Monday — so "this week" is always populated and the
 * suite never depends on the Python API being up.
 */

const rangeLabel = (page: Page) => page.getByTestId('range-label')

const openViewMenu = async (page: Page) => {
  await page.getByRole('button', { name: /^(Day|Three Day|Working Week|Week|Month)$/ }).click()
  await expect(page.getByRole('menuitemcheckbox', { name: 'List' })).toBeVisible()
}

const pickRange = async (page: Page, name: string) => {
  await openViewMenu(page)
  await page.getByRole('menuitemradio', { name, exact: true }).click()
  await page.keyboard.press('Escape')
}

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'NoShow Planner' })).toBeVisible()
})

test('loads the week calendar with this week\'s appointments', async ({ page }) => {
  await expect(page.getByTestId('calendar-view')).toBeVisible()
  await expect(page.getByText('Intake - John Doe')).toBeVisible()
  await expect(page.getByText('Controle - Jane Smith')).toBeVisible()
})

test('hides canceled appointments', async ({ page }) => {
  // Fixture id 3 is canceled: it is absent from the grid and from the list.
  await expect(page.getByText('Nacontrole - Pieter de Vries')).toHaveCount(0)

  await openViewMenu(page)
  await page.getByRole('menuitemcheckbox', { name: 'List' }).click()
  await page.keyboard.press('Escape')
  await expect(page.getByTestId('list-view')).toBeVisible()

  await expect(page.getByText('Nacontrole - Pieter de Vries')).toHaveCount(0)
})

test('shows the waitlist ordered by priority', async ({ page }) => {
  const cards = page.locator('[data-waitlist-item]')

  await expect(cards).toHaveCount(3)
  await expect(cards.first()).toContainText('Youssef Bakkali')
  await expect(cards.first()).toContainText('P1')
})

test('each range changes the visible span and Today returns to now', async ({ page }) => {
  const weekLabel = await rangeLabel(page).textContent()

  await pickRange(page, 'Day')
  await expect(rangeLabel(page)).not.toHaveText(weekLabel ?? '')
  await expect(page.locator('.fc-timeGridDay-view')).toBeVisible()

  await pickRange(page, 'Three Day')
  await expect(page.locator('.fc-timeGridThreeDay-view')).toBeVisible()

  await pickRange(page, 'Working Week')
  await expect(page.locator('.fc-timeGridWorkWeek-view')).toBeVisible()
  // Saturday and Sunday are hidden in the working week.
  await expect(page.locator('.fc-col-header-cell')).toHaveCount(5)

  await pickRange(page, 'Month')
  await expect(page.locator('.fc-dayGridMonth-view')).toBeVisible()

  await pickRange(page, 'Week')
  await expect(rangeLabel(page)).toHaveText(weekLabel ?? '')

  // Paging away and pressing Today comes back to the same span.
  await page.getByRole('button', { name: 'Next period' }).click()
  await expect(rangeLabel(page)).not.toHaveText(weekLabel ?? '')
  // Both the sidebar and the toolbar have a Today button; this is the toolbar's.
  await page.getByRole('main').getByRole('button', { name: 'Today' }).click()
  await expect(rangeLabel(page)).toHaveText(weekLabel ?? '')
})

test('List switches the view and preserves the selected range', async ({ page }) => {
  await pickRange(page, 'Three Day')
  const threeDayLabel = await rangeLabel(page).textContent()

  await openViewMenu(page)
  await page.getByRole('menuitemcheckbox', { name: 'List' }).click()
  await page.keyboard.press('Escape')

  await expect(page.getByTestId('list-view')).toBeVisible()
  await expect(page.getByTestId('calendar-view')).toHaveCount(0)
  await expect(rangeLabel(page)).toHaveText(threeDayLabel ?? '')
  // The range stays ticked alongside List — they are orthogonal.
  await openViewMenu(page)
  await expect(
    page.getByRole('menuitemradio', { name: 'Three Day', exact: true }),
  ).toHaveAttribute(
    'aria-checked',
    'true',
  )
  await expect(page.getByRole('menuitemcheckbox', { name: 'List' })).toHaveAttribute(
    'aria-checked',
    'true',
  )
})

test('clicking an appointment opens its details, and delete removes it', async ({ page }) => {
  await page.getByText('Intake - John Doe').click()

  const details = page.getByTestId('appointment-details')
  await expect(details).toBeVisible()
  await expect(details).toContainText('John Doe')
  await expect(details).toContainText('09:00 to 10:00')

  await details.getByRole('button', { name: 'Delete Event' }).click()

  await expect(page.getByText('Intake - John Doe')).toHaveCount(0)
  // Still gone after the refetch that follows the mutation.
  await page.waitForTimeout(300)
  await expect(page.getByText('Intake - John Doe')).toHaveCount(0)
  await expect(page.getByText('Controle - Jane Smith')).toBeVisible()
})

test('rescheduling from the edit modal moves the appointment', async ({ page }) => {
  await page.getByText('Controle - Jane Smith').click()
  await page.getByTestId('appointment-details').getByRole('button', { name: 'Edit Event' }).click()

  await expect(page.getByText('Alternative times')).toBeVisible()
  const firstOption = page.getByRole('radio').first()
  await firstOption.click()
  await page.getByRole('button', { name: 'Reschedule' }).click()

  await expect(page.getByText('Alternative times')).toHaveCount(0)
  await expect(page.getByText('Controle - Jane Smith')).toBeVisible()
})

test('dragging a waitlist card onto a free slot schedules the patient', async ({ page }) => {
  const card = page.locator('[data-waitlist-item]').first()
  await expect(card).toContainText('Youssef Bakkali')

  // A quiet corner of the grid: late afternoon on the first visible day.
  const target = page.locator('.fc-timegrid-col.fc-day').first()
  const cardBox = await card.boundingBox()
  const targetBox = await target.boundingBox()
  if (!cardBox || !targetBox) throw new Error('Could not locate the drag source or target')

  // Manual mouse steps: HTML5 drag emulation is flaky across browsers.
  await page.mouse.move(cardBox.x + cardBox.width / 2, cardBox.y + cardBox.height / 2)
  await page.mouse.down()
  await page.mouse.move(targetBox.x + targetBox.width / 2, targetBox.y + targetBox.height * 0.8, {
    steps: 20,
  })
  await page.mouse.up()

  // The patient is now on the grid and off the waitlist.
  await expect(
    page.getByTestId('event-chip').filter({ hasText: 'Youssef Bakkali' }),
  ).toHaveCount(1)
  await expect(page.locator('[data-waitlist-item]')).toHaveCount(2)
})

test('an appointment drags to a new time but keeps its length', async ({ page }) => {
  const chip = page.getByTestId('event-chip').filter({ hasText: 'Controle - Jane Smith' })
  await expect(chip).toContainText('11:00 - 11:30')

  const event = page.locator('.fc-event').filter({ hasText: 'Controle - Jane Smith' })
  const box = await event.boundingBox()
  if (!box) throw new Error('Could not locate the appointment chip')

  // Manual mouse steps; FullCalendar drives its own pointer handling and only
  // starts a drag after the pointer has moved a few pixels.
  await page.mouse.move(box.x + box.width / 2, box.y + 6)
  await page.mouse.down()
  await page.mouse.move(box.x + box.width / 2, box.y + 16, { steps: 5 })
  await page.mouse.move(box.x + box.width / 2, box.y + 126, { steps: 20 })
  await page.mouse.up()

  await expect(chip).not.toContainText('11:00 - 11:30')
  // Position, not size: still a 30-minute appointment.
  const moved = (await chip.textContent()) ?? ''
  const [from, to] = moved.match(/\d{2}:\d{2}/g) ?? ['00:00', '00:00']
  const minutes = (value: string) => Number(value.slice(0, 2)) * 60 + Number(value.slice(3))
  expect(minutes(to) - minutes(from)).toBe(30)
})

test('both sidebars collapse and the state survives a reload', async ({ page }) => {
  // AppShell collapses by sliding the panel out of the viewport rather than
  // unmounting it, so viewport membership is the honest assertion here.
  const aside = page.locator('aside')
  const navbar = page.locator('nav')

  await expect(aside).toBeInViewport()
  await expect(navbar).toBeInViewport()

  await page.getByRole('button', { name: 'Toggle waitlist' }).click()
  await expect(aside).not.toBeInViewport()

  await page.getByRole('button', { name: 'Toggle date navigation' }).click()
  await expect(navbar).not.toBeInViewport()

  await page.reload()
  await expect(page.getByRole('heading', { name: 'NoShow Planner' })).toBeVisible()
  await expect(aside).not.toBeInViewport()
  await expect(navbar).not.toBeInViewport()
})
