import { expect, test } from '@playwright/test'

// AddEdit requires auth. Unauthenticated users are redirected to /login.
// Full form tests require a real authenticated session (Google OAuth).

test.describe('AddEdit — auth redirect', () => {
  test('redirects /bills/new to /login when unauthenticated', async ({ page }) => {
    await page.goto('/bills/new')
    await page.waitForTimeout(1500)
    expect(page.url()).toContain('/login')
  })
})

// Notes on authenticated form tests (require real Google session):
//   - Vuetify v-form with native validation
//   - CategoryPicker: v-item-group, one category active at a time
//   - Date field: v-text-field with DD/MM/AAAA placeholder and parseDate() conversion
//   - Save button: color="primary", type="submit", disabled when loading
//   - Cancel button: variant="text", calls router.back()
//   - AI scan section: visible only on /bills/new (isNew computed)
//   - Drive connected: shows "Escanear y archivar en Drive" option
//   - Drive disconnected: shows only "Solo escanear" option
