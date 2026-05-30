import { expect, test } from '@playwright/test'

// All routes now require auth — unauthenticated users are redirected to /login.
// Responsive tests verify that /login itself renders correctly at all viewports,
// and that the auth redirect works across viewport sizes.

const VIEWPORTS = {
  mobile_sm:  { width: 375,  height: 667  },
  mobile_lg:  { width: 430,  height: 932  },
  desktop:    { width: 1280, height: 800  },
  desktop_xl: { width: 1920, height: 1080 },
}

for (const [name, viewport] of Object.entries(VIEWPORTS)) {
  test.describe(`Responsive — ${name} (${viewport.width}×${viewport.height})`, () => {
    test.use({ viewport })

    test('login page renders without overflow', async ({ page }) => {
      await page.goto('/login')
      await page.waitForLoadState('networkidle')
      const bodyWidth = await page.evaluate(() => document.body.scrollWidth)
      expect(bodyWidth).toBeLessThanOrEqual(viewport.width + 30)
    })

    test('login page has Google button visible', async ({ page }) => {
      await page.goto('/login')
      await page.waitForLoadState('networkidle')
      const btn = page.getByRole('button', { name: /continuar con google/i })
      await expect(btn).toBeVisible()
    })

    test('protected routes redirect to /login', async ({ page }) => {
      await page.goto('/')
      await page.waitForTimeout(1500)
      expect(page.url()).toContain('/login')
    })

    test('no horizontal overflow on login page', async ({ page }) => {
      await page.goto('/login')
      await page.waitForLoadState('networkidle')
      const overflow = await page.evaluate(() => {
        return document.body.offsetWidth > window.innerWidth + 20
      })
      expect(overflow).toBe(false)
    })
  })
}

// Desktop-specific layout checks (require auth — spec for CI with mocked auth)
test.describe('Responsive — desktop layout expectations', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test('at 1280px login card is centered', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('networkidle')
    const card = page.locator('.v-card').first()
    await expect(card).toBeVisible()
    const box = await card.boundingBox()
    if (box) {
      // Card should be roughly centered — not at the very left edge
      expect(box.x).toBeGreaterThan(100)
    }
  })
})

// Note: Tests for navigation drawer (desktop) and bottom nav (mobile)
// require an authenticated session. Structure:
//   - Desktop ≥960px: v-navigation-drawer visible, v-bottom-navigation NOT visible
//   - Mobile <960px: v-bottom-navigation visible, v-navigation-drawer NOT visible
//   These are validated manually after authentication.
