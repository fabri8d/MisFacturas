import { expect, test } from '@playwright/test'

test.describe('History view', () => {
  test('loads chart canvas', async ({ page }) => {
    await page.goto('/history')
    await expect(page.locator('canvas')).toBeVisible({ timeout: 8000 })
  })

  test('summary table has 6 rows', async ({ page }) => {
    await page.goto('/history')
    // Esperar a que cargue la tabla
    await page.waitForSelector('table tbody tr', { timeout: 8000 })
    const rows = await page.locator('table tbody tr').count()
    expect(rows).toBe(6)
  })

  test('shows page title', async ({ page }) => {
    await page.goto('/history')
    // Usar h1 para evitar ambigüedad con el ítem "Historial" del bottom nav
    await expect(page.locator('h1.page-title')).toBeVisible()
    await expect(page.locator('h1.page-title')).toContainText('Historial')
  })

  test('legend shows Total and Pagado', async ({ page }) => {
    await page.goto('/history')
    await expect(page.locator('.legend')).toBeVisible()
    await expect(page.locator('.legend-item').filter({ hasText: 'Total' })).toBeVisible()
    await expect(page.locator('.legend-item').filter({ hasText: 'Pagado' })).toBeVisible()
  })
})
