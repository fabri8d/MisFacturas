import { expect, test } from '@playwright/test'

// History requires auth — redirects to /login for unauthenticated users.
// Full end-to-end tests require a real authenticated session.
// The computed/store logic is covered by unit tests in src/tests/views/HistoryView.test.js

test.describe('History — auth redirect', () => {
  test('redirects unauthenticated user to /login', async ({ page }) => {
    await page.goto('/history')
    await page.waitForTimeout(1500)
    expect(page.url()).toContain('/login')
  })

  test('login page visible after redirect from /history', async ({ page }) => {
    await page.goto('/history')
    await page.waitForTimeout(1500)
    await expect(page.locator('text=MisFacturas')).toBeVisible()
    const btn = page.getByRole('button', { name: /continuar con google/i })
    await expect(btn).toBeVisible()
  })
})

// Note: the following tests validate structure — they'll run when auth is mocked in CI
// or with a real session. For now they serve as spec documentation.
//
// test('history shows current year header', ...)
// test('history table has 12 rows', ...)
// test('chart canvas#historyChart is visible', ...)
// test('prev year navigation decrements year', ...)
// test('next year disabled at current year', ...)
// test('annual totals cards visible', ...)
