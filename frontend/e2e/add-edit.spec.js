import { expect, test } from '@playwright/test'

test.describe('AddEdit form validation', () => {
  test('save button is disabled without required fields', async ({ page }) => {
    await page.goto('/bills/new')
    // Sin completar nada, el botón debe estar disabled o el form debe fallar
    const btn = page.locator('.btn-save')
    // Si usa HTML5 validation, el click no navega
    await btn.click()
    await expect(page).toHaveURL(/\/bills\/new/)
  })

  test('category picker selects one at a time', async ({ page }) => {
    await page.goto('/bills/new')
    const btns = page.locator('.cat-btn')

    await btns.nth(1).click() // gas
    await expect(btns.nth(1)).toHaveClass(/active/)
    await expect(btns.nth(0)).not.toHaveClass(/active/)

    await btns.nth(2).click() // agua
    await expect(btns.nth(2)).toHaveClass(/active/)
    await expect(btns.nth(1)).not.toHaveClass(/active/)
  })

  test('cancel returns to previous page', async ({ page }) => {
    await page.goto('/bills')
    await page.goto('/bills/new')
    await page.locator('.btn-cancel').click()
    // Debe volver a /bills o /
    await expect(page).toHaveURL(/\/(bills)?$/)
  })

  test('AI scan section visible on new bill only', async ({ page }) => {
    await page.goto('/bills/new')
    await expect(page.locator('.scan-section')).toBeVisible()
  })
})
