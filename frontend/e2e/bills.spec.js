import { expect, test } from '@playwright/test'

// Último día del mes actual — garantiza que la factura queda en el mes que muestra BillsView
const today = new Date()
const inCurrentMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0)
  .toISOString().slice(0, 10)

test.describe('Bills list', () => {
  test('navigates to /bills from bottom nav', async ({ page }) => {
    await page.goto('/')
    await page.locator('.nav-item').nth(1).click()
    await expect(page).toHaveURL(/\/bills/)
  })

  test('shows + Nueva button', async ({ page }) => {
    await page.goto('/bills')
    await expect(page.locator('.add-btn')).toBeVisible()
  })
})

test.describe('Create bill', () => {
  test('creates a bill manually end-to-end', async ({ page }) => {
    await page.goto('/bills/new')
    await page.locator('.cat-btn').first().click()
    await page.fill('#name', 'Test EPEC E2E')
    await page.fill('#amount', '15000')
    await page.fill('#dueDate', inCurrentMonth)
    await page.locator('.btn-save').click()

    await page.waitForURL('**/bills')
    // Esperar a que la lista cargue desde la API antes de buscar el texto
    await page.waitForSelector('.bill-row', { timeout: 10000 })
    await expect(page.locator('.bill-row').filter({ hasText: 'Test EPEC E2E' })).toBeVisible()
  })

  test('mark bill as paid toggles status', async ({ page }) => {
    await page.goto('/bills/new')
    await page.locator('.cat-btn').first().click()
    await page.fill('#name', 'Toggle Paid Test')
    await page.fill('#amount', '5000')
    await page.fill('#dueDate', inCurrentMonth)
    await page.locator('.btn-save').click()
    await page.waitForURL('**/bills')
    await page.waitForSelector('.bill-row', { timeout: 10000 })

    const row = page.locator('.bill-row', { hasText: 'Toggle Paid Test' })
    await row.locator('.check').click()
    await expect(row.locator('.badge.paid')).toBeVisible()
  })

  test('delete bill with confirmation', async ({ page }) => {
    await page.goto('/bills/new')
    await page.locator('.cat-btn').first().click()
    await page.fill('#name', 'Delete Me E2E')
    await page.fill('#amount', '1000')
    await page.fill('#dueDate', inCurrentMonth)
    await page.locator('.btn-save').click()
    await page.waitForURL('**/bills')
    await page.waitForSelector('.bill-row', { timeout: 10000 })

    const row = page.locator('.bill-row', { hasText: 'Delete Me E2E' })
    page.on('dialog', dialog => dialog.accept())
    await row.locator('.icon-btn.danger').click()

    await expect(page.locator('.bill-row').filter({ hasText: 'Delete Me E2E' })).not.toBeVisible()
  })

  test('edit bill prefills form', async ({ page }) => {
    await page.goto('/bills/new')
    await page.locator('.cat-btn').first().click()
    await page.fill('#name', 'Edit Me E2E')
    await page.fill('#amount', '2500')
    await page.fill('#dueDate', inCurrentMonth)
    await page.locator('.btn-save').click()
    await page.waitForURL('**/bills')
    await page.waitForSelector('.bill-row', { timeout: 10000 })

    const row = page.locator('.bill-row', { hasText: 'Edit Me E2E' })
    await row.locator('.icon-btn:not(.danger)').click()
    await page.waitForURL(/\/bills\/.+/)

    await expect(page.locator('#name')).toHaveValue('Edit Me E2E')
    await expect(page.locator('#amount')).toHaveValue('2500')
  })
})
