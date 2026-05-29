import { expect, test } from '@playwright/test'

test.describe('Dashboard', () => {
  test('loads and shows main elements', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('MisFacturas')).toBeVisible()
    await expect(page.locator('.month-nav')).toBeVisible()
    await expect(page.locator('.stat-card')).toHaveCount(3)
  })

  test('shows Total, Pagado, Pendiente stat cards', async ({ page }) => {
    await page.goto('/')
    // Usar .stat-card para evitar ambigüedad con ProgressBar que también tiene "Pagado"
    await expect(page.locator('.stat-card').filter({ hasText: 'Total' }).first()).toBeVisible()
    await expect(page.locator('.stat-card').filter({ hasText: 'Pagado' }).first()).toBeVisible()
    await expect(page.locator('.stat-card').filter({ hasText: 'Pendiente' }).first()).toBeVisible()
  })

  test('month navigation changes label', async ({ page }) => {
    await page.goto('/')
    const label = page.locator('.month-nav .label')
    const initialText = await label.textContent()

    await page.locator('.month-nav button').first().click()
    const prevText = await label.textContent()
    expect(prevText).not.toBe(initialText)

    await page.locator('.month-nav button').last().click()
    await expect(label).toHaveText(initialText ?? '')
  })

  test('shows empty state when no bills', async ({ page }) => {
    await page.goto('/')
    // Si no hay facturas debe mostrar algún mensaje o la lista vacía
    const list = page.locator('.list')
    const emptyMsg = page.locator('.empty')
    const hasBills = await list.locator('.bill-row').count()
    if (hasBills === 0) {
      await expect(emptyMsg.or(page.getByText('No hay facturas'))).toBeVisible()
    }
  })

  test('bottom navigation has 4 items', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('.nav-item')).toHaveCount(4)
  })
})
