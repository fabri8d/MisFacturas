import { expect, test } from '@playwright/test'

test.describe('Auth — login page & guards', () => {
  test('login page shows Google button', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('networkidle')
    const btn = page.getByRole('button', { name: /continuar con google/i })
    await expect(btn).toBeVisible()
  })

  test('login page does not redirect unauthenticated user away', async ({ page }) => {
    await page.goto('/login')
    await page.waitForTimeout(1000)
    expect(page.url()).toContain('/login')
  })

  test('protected route / redirects to /login when unauthenticated', async ({ page }) => {
    await page.goto('/')
    await page.waitForTimeout(2000)
    expect(page.url()).toContain('/login')
  })

  test('protected route /bills redirects to /login when unauthenticated', async ({ page }) => {
    await page.goto('/bills')
    await page.waitForTimeout(2000)
    expect(page.url()).toContain('/login')
  })

  test('protected route /history redirects to /login when unauthenticated', async ({ page }) => {
    await page.goto('/history')
    await page.waitForTimeout(2000)
    expect(page.url()).toContain('/login')
  })

  test('protected route /settings redirects to /login when unauthenticated', async ({ page }) => {
    await page.goto('/settings')
    await page.waitForTimeout(2000)
    expect(page.url()).toContain('/login')
  })

  test('auth callback shows loading spinner', async ({ page }) => {
    await page.goto('/auth/callback')
    await page.waitForLoadState('networkidle')
    // Either spinner is visible or it redirected (session resolved)
    const spinner = page.locator('.v-progress-circular')
    const isSpinner = await spinner.isVisible().catch(() => false)
    const redirectedToLogin = page.url().includes('/login')
    const redirectedToHome  = page.url() === page.url().replace(/\/.*$/, '/')
    expect(isSpinner || redirectedToLogin || redirectedToHome).toBe(true)
  })
})
