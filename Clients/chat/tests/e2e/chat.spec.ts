import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

/**
 * Runs against the MSW handlers in `src/mocks` (`npm run dev:mock`), so the
 * suite is deterministic and never needs the Python API on port 8080.
 */

const patientSelect = (page: Page) => page.getByRole('combobox', { name: 'Patient' })
const messages = (page: Page) => page.getByTestId('message')

const choosePatient = async (page: Page, label: string) => {
  await patientSelect(page).click()
  await page.getByRole('option', { name: label }).click()
}

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'NoShow Chat' })).toBeVisible()
})

test('starts with the patient selector and an empty state', async ({ page }) => {
  await expect(patientSelect(page)).toBeVisible()
  await expect(page.getByText('Select a patient to view the conversation.')).toBeVisible()
})

test('selecting a patient updates the URL and shows the conversation', async ({ page }) => {
  await choosePatient(page, 'Jane Smith (#2)')

  await expect(page).toHaveURL(/patientId=2/)
  await expect(page.getByText('Hello Jane, a new timeslot is available.')).toBeVisible()
  await expect(messages(page)).toHaveCount(1)
})

test('deep-links to a patient', async ({ page }) => {
  await page.goto('/?patientId=1')

  await expect(patientSelect(page)).toHaveValue('John Doe (#1)')
  await expect(messages(page)).toHaveCount(3)
  await expect(page.getByText('Wednesday 10:30 — shall I book it?')).toBeVisible()
})

test('polls from -1 and then from the highest id on screen', async ({ page }) => {
  const first = page.waitForRequest((req) => req.url().includes('/api/v1/recent-messages/1/'))
  await page.goto('/?patientId=1')
  expect(new URL((await first).url()).pathname).toBe('/api/v1/recent-messages/1/-1')

  await expect(messages(page)).toHaveCount(3)
  const next = await page.waitForRequest((req) => req.url().includes('/api/v1/recent-messages/1/'))
  expect(new URL(next.url()).pathname).toBe('/api/v1/recent-messages/1/4')
})

test('sends a message and continues polling after it', async ({ page }) => {
  await page.goto('/?patientId=2')
  await expect(messages(page)).toHaveCount(1)

  const composer = page.getByRole('textbox', { name: 'Message' })
  await composer.fill('See you Wednesday')
  await composer.press('Enter')

  await expect(page.getByText('See you Wednesday')).toBeVisible()
  await expect(messages(page)).toHaveCount(2)
  await expect(messages(page).last()).toHaveAttribute('data-role', 'user')
  await expect(composer).toHaveValue('')

  const poll = await page.waitForRequest((req) => req.url().includes('/api/v1/recent-messages/2/101'))
  expect(poll).toBeTruthy()
  // Nothing doubles up once the poll has echoed the sent message back.
  await expect(messages(page)).toHaveCount(2)
})

test('shows messages that arrive server-side without user action', async ({ page }) => {
  await page.goto('/?patientId=3')
  await expect(messages(page)).toHaveCount(2)

  // Runs in the browser; the node tsconfig has no DOM lib, hence the cast.
  await page.evaluate(() => {
    const hook = (globalThis as { __pushMessage?: (input: object) => void }).__pushMessage
    hook?.({ patient_id: 3, role: 'assistant', content: 'The slot is booked.' })
  })

  await expect(page.getByText('The slot is booked.')).toBeVisible({ timeout: 5_000 })
  await expect(messages(page)).toHaveCount(3)
})

test('switching patient replaces the conversation and Back restores it', async ({ page }) => {
  await page.goto('/?patientId=1')
  await expect(messages(page)).toHaveCount(3)

  await choosePatient(page, 'Youssef Bakkali (#6)')
  await expect(page).toHaveURL(/patientId=6/)
  await expect(page.getByText('No messages yet.')).toBeVisible()
  await expect(messages(page)).toHaveCount(0)

  await page.goBack()
  await expect(page).toHaveURL(/patientId=1/)
  await expect(patientSelect(page)).toHaveValue('John Doe (#1)')
  await expect(messages(page)).toHaveCount(3)
})
