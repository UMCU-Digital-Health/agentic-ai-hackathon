import { expect, test } from '@playwright/test'

test('shows the heading', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: /get started/i })).toBeVisible()
})

test('increments the counter', async ({ page }) => {
  await page.goto('/')

  const button = page.getByRole('button', { name: /count is/i })
  await expect(button).toHaveText(/count is 0/i)

  await button.click()

  await expect(button).toHaveText(/count is 1/i)
})
