import { expect, test } from '@playwright/test'

// All bill routes require auth. Unauthenticated users are redirected to /login.
// Full CRUD tests require a real authenticated session (Google OAuth).

test.describe('Bills — auth redirect', () => {
  test('GET /bills redirects unauthenticated user to /login', async ({ page }) => {
    await page.goto('/bills')
    await page.waitForTimeout(1500)
    expect(page.url()).toContain('/login')
  })

  test('GET /bills/new redirects unauthenticated user to /login', async ({ page }) => {
    await page.goto('/bills/new')
    await page.waitForTimeout(1500)
    expect(page.url()).toContain('/login')
  })
})

// Notes on authenticated tests (require real Google session):
//   Bills list:
//     - MonthNav displays current month
//     - FAB mdi-plus button visible (navigates to /bills/new)
//     - Mobile: v-list with BillRow items
//     - Desktop: v-data-table with sortable columns
//   Create bill:
//     - Form with category picker, name, amount, date fields
//     - AI scan section visible
//     - Save navigates back to /bills
//   Edit bill:
//     - Form prefilled with existing bill data
//   Delete bill:
//     - Confirm dialog, bill removed from list
//   Toggle paid:
//     - isPaid status chip updates
