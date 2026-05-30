import { expect, test } from '@playwright/test'

// Receipt features require auth. These tests verify auth redirect behavior
// and the API security layer. Full flow tests require a real authenticated session.

test.describe('Receipts — auth protection', () => {
  test('GET /api/bills/receipts/summary requires auth', async ({ request }) => {
    const r = await request.get('/api/bills/receipts/summary')
    expect([401, 422]).toContain(r.status())
  })

  test('POST /api/bills/fake-id/receipts requires auth', async ({ request }) => {
    const r = await request.post('/api/bills/fake-id/receipts')
    expect([401, 422]).toContain(r.status())
  })

  test('GET /api/bills/fake-id/receipts requires auth', async ({ request }) => {
    const r = await request.get('/api/bills/fake-id/receipts')
    expect([401, 422]).toContain(r.status())
  })
})

test.describe('Receipts — redirect for unauthenticated users', () => {
  test('navigating to /bills redirects to /login', async ({ page }) => {
    await page.goto('/bills')
    await page.waitForTimeout(1500)
    expect(page.url()).toContain('/login')
  })
})

// Notes on authenticated receipt tests (require real Google OAuth + Drive connected):
//   test_receipt_chip_visible_after_upload:
//     After uploading a receipt, ReceiptChip shows count in BillRow
//   test_open_receipt_panel_from_chip:
//     Click chip → ReceiptPanel dialog opens with "Comprobantes" title
//   test_receipt_panel_shows_drive_link:
//     Panel receipt item has "Ver en Drive" button enabled with href
//   test_add_edit_shows_drive_tabs_when_connected:
//     /bills/new with Drive connected → two tabs visible
//   test_add_edit_no_drive_shows_single_option:
//     /bills/new without Drive → only local scan option
