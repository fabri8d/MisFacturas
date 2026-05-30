import { expect, test } from '@playwright/test'

test.describe('Security — API protection', () => {
  test('GET /api/bills without token returns 401 or 422', async ({ request }) => {
    const r = await request.get('/api/bills')
    expect([401, 422]).toContain(r.status())
  })

  test('GET /api/bills with invalid token returns 401', async ({ request }) => {
    const r = await request.get('/api/bills', {
      headers: { Authorization: 'Bearer invalid_token_xyz' },
    })
    expect(r.status()).toBe(401)
  })

  test('POST /api/bills without token is rejected', async ({ request }) => {
    const r = await request.post('/api/bills', {
      data: { name: 'Hack', category: 'otro', amount: 1, dueDate: '2026-12-01' },
    })
    expect([401, 422]).toContain(r.status())
  })

  test('health endpoint is public', async ({ request }) => {
    const r = await request.get('/api/health')
    expect(r.status()).toBe(200)
    const body = await r.json()
    expect(body.status).toBe('ok')
  })
})

test.describe('Security — sensitive data not in HTML', () => {
  test('login page HTML does not contain service key patterns', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('networkidle')
    const html = await page.content()
    // service_role keys start with eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 and are very long
    // ANON key is intentionally embedded (it's public) — check no SERVICE key leaks
    // We can't know the actual service key, but we can verify no 'service_role' string appears
    expect(html).not.toContain('service_role')
    expect(html).not.toContain('SUPABASE_SERVICE_KEY')
    expect(html).not.toContain('GROQ_API_KEY')
  })
})
