import { expect, test } from '@playwright/test'

const VIEWPORTS = {
  mobile_sm:  { width: 375,  height: 667  },
  mobile_lg:  { width: 430,  height: 932  },
  tablet:     { width: 768,  height: 1024 },
  desktop:    { width: 1280, height: 800  },
  desktop_xl: { width: 1920, height: 1080 },
}

for (const [name, viewport] of Object.entries(VIEWPORTS)) {
  test.describe(`Responsive — ${name} (${viewport.width}×${viewport.height})`, () => {
    test.use({ viewport })

    test('bottom nav is visible and fits', async ({ page }) => {
      await page.goto('/')
      const nav = page.locator('.bottom-nav')
      await expect(nav).toBeVisible()
      const navItems = page.locator('.nav-item')
      await expect(navItems).toHaveCount(4)

      // Ningún ítem fuera del viewport
      const navBox = await nav.boundingBox()
      if (navBox) expect(navBox.width).toBeLessThanOrEqual(viewport.width)
    })

    test('content does not overflow horizontally', async ({ page }) => {
      await page.goto('/')
      const bodyWidth = await page.evaluate(() => document.body.scrollWidth)
      expect(bodyWidth).toBeLessThanOrEqual(viewport.width + 5) // +5px tolerancia scroll
    })

    test('content max-width respected on desktop', async ({ page }) => {
      if (viewport.width < 680) return
      await page.goto('/')
      const content = page.locator('.content')
      const box = await content.boundingBox()
      if (box) expect(box.width).toBeLessThanOrEqual(700) // ~680px + padding
    })

    test('bill form accessible', async ({ page }) => {
      await page.goto('/bills/new')
      await expect(page.locator('#name')).toBeVisible()
      await expect(page.locator('#amount')).toBeVisible()
      await expect(page.locator('#dueDate')).toBeVisible()
      await expect(page.locator('.btn-save')).toBeVisible()
    })

    test('category picker buttons are tappable (min 44px area)', async ({ page }) => {
      await page.goto('/bills/new')
      const btn = page.locator('.cat-btn').first()
      const box = await btn.boundingBox()
      if (box) {
        expect(box.width).toBeGreaterThanOrEqual(44)
        expect(box.height).toBeGreaterThanOrEqual(44)
      }
    })

    test('MonthNav fits without overflow', async ({ page }) => {
      await page.goto('/')
      const nav = page.locator('.month-nav')
      await expect(nav).toBeVisible()
      const box = await nav.boundingBox()
      if (box) expect(box.width).toBeLessThanOrEqual(viewport.width)
    })

    test('chart renders without horizontal overflow', async ({ page }) => {
      await page.goto('/history')
      const canvas = page.locator('canvas')
      await expect(canvas).toBeVisible({ timeout: 8000 })
      const box = await canvas.boundingBox()
      if (box) expect(box.width).toBeLessThanOrEqual(viewport.width)
    })

    test('navigation between all views works', async ({ page }) => {
      await page.goto('/')
      // Facturas
      await page.locator('.nav-item').nth(1).click()
      await expect(page).toHaveURL(/\/bills/)
      // Historial
      await page.locator('.nav-item').nth(2).click()
      await expect(page).toHaveURL(/\/history/)
      // Ajustes
      await page.locator('.nav-item').nth(3).click()
      await expect(page).toHaveURL(/\/settings/)
      // Inicio
      await page.locator('.nav-item').nth(0).click()
      await expect(page).toHaveURL(/\/$/)
    })
  })
}
