import { expect, test } from '@playwright/test'

// All dashboard routes require auth. Unauthenticated users are redirected to /login.
// Full dashboard tests require a real authenticated session (Google OAuth).

test.describe('Dashboard — auth redirect', () => {
  test('redirects unauthenticated user to /login', async ({ page }) => {
    await page.goto('/')
    await page.waitForTimeout(1500)
    expect(page.url()).toContain('/login')
  })

  test('login page shows MisFacturas branding', async ({ page }) => {
    await page.goto('/')
    await page.waitForTimeout(1500)
    await expect(page.locator('text=MisFacturas')).toBeVisible()
  })

  test('login page has Google sign-in button', async ({ page }) => {
    await page.goto('/')
    await page.waitForTimeout(1500)
    const btn = page.getByRole('button', { name: /continuar con google/i })
    await expect(btn).toBeVisible()
  })
})

// Notes on authenticated tests (require real Google session):
//   - MisFacturas title visible in app bar
//   - MonthNav chip shows current month
//   - 3 stat cards: Total, Pagado, Pendiente
//   - ProgressBar visible
//   - Mobile: v-bottom-navigation with 4 items
//   - Desktop: v-navigation-drawer visible, bottom nav hidden
//   - Desktop: 2-column layout with bills left, sidebar right
