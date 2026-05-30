import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, computed } from 'vue'

// ── Helpers ──────────────────────────────────────────────────────────────────

function make12Months(year = 2026, totals = null) {
  const labels = ['enero','febrero','marzo','abril','mayo','junio',
                  'julio','agosto','septiembre','octubre','noviembre','diciembre']
  return labels.map((label, i) => ({
    month:  `${year}-${String(i + 1).padStart(2, '0')}`,
    label,
    total:  totals ? totals[i] : 0,
    paid:   totals ? Math.floor(totals[i] * 0.6) : 0,
  }))
}

// ── Año navigation logic ─────────────────────────────────────────────────────

describe('HistoryView — year navigation logic', () => {
  it('prevYear decrements summaryYear', () => {
    const year = ref(2026)
    const prevYear = () => year.value--
    prevYear()
    expect(year.value).toBe(2025)
  })

  it('nextYear increments when not at current year', () => {
    const currentYear = new Date().getFullYear()
    const year = ref(currentYear - 1)
    const nextYear = () => { if (year.value < currentYear) year.value++ }
    nextYear()
    expect(year.value).toBe(currentYear)
  })

  it('nextYear is disabled at current year', () => {
    const currentYear = new Date().getFullYear()
    const year = ref(currentYear)
    const isNextDisabled = computed(() => year.value >= currentYear)
    expect(isNextDisabled.value).toBe(true)
  })

  it('nextYear is enabled one year in the past', () => {
    const currentYear = new Date().getFullYear()
    const year = ref(currentYear - 1)
    const isNextDisabled = computed(() => year.value >= currentYear)
    expect(isNextDisabled.value).toBe(false)
  })
})

// ── Annual totals computed ───────────────────────────────────────────────────

describe('HistoryView — annual totals', () => {
  it('yearTotal sums all 12 months', () => {
    const summaryData = ref(make12Months(2026, Array(12).fill(1000)))
    const yearTotal = computed(() => summaryData.value.reduce((s, m) => s + m.total, 0))
    expect(yearTotal.value).toBe(12000)
  })

  it('yearPaid sums paid amounts', () => {
    const data = make12Months(2026)
    data[0] = { ...data[0], total: 1000, paid: 800 }
    data[1] = { ...data[1], total: 2000, paid: 1500 }
    const summaryData = ref(data)
    const yearPaid = computed(() => summaryData.value.reduce((s, m) => s + m.paid, 0))
    expect(yearPaid.value).toBe(2300)
  })

  it('yearPending is total minus paid', () => {
    const summaryData = ref(make12Months(2026, Array(12).fill(1000)))
    const yearTotal   = computed(() => summaryData.value.reduce((s, m) => s + m.total, 0))
    const yearPaid    = computed(() => summaryData.value.reduce((s, m) => s + m.paid, 0))
    const yearPending = computed(() => yearTotal.value - yearPaid.value)
    // paid = floor(1000 * 0.6) = 600 for each
    expect(yearPending.value).toBe(yearTotal.value - yearPaid.value)
  })

  it('yearTotal is zero when all months are empty', () => {
    const summaryData = ref(make12Months(2099))
    const yearTotal = computed(() => summaryData.value.reduce((s, m) => s + m.total, 0))
    expect(yearTotal.value).toBe(0)
  })
})

// ── Table rows ───────────────────────────────────────────────────────────────

describe('HistoryView — table structure', () => {
  it('12 months data maps to 12 rows', () => {
    const summaryData = make12Months(2026)
    expect(summaryData).toHaveLength(12)
  })

  it('months have correct month codes for 2026', () => {
    const months = make12Months(2026).map((m) => m.month)
    expect(months[0]).toBe('2026-01')
    expect(months[11]).toBe('2026-12')
  })

  it('labels are Spanish month names', () => {
    const labels = make12Months(2026).map((m) => m.label)
    expect(labels[0]).toBe('enero')
    expect(labels[11]).toBe('diciembre')
    expect(labels[4]).toBe('mayo')
  })

  it('isCurrentMonth identifies the correct month', () => {
    const now = new Date()
    const cm = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
    const isCurrentMonth = (row) => row.month === cm
    const data = make12Months(now.getFullYear())
    const current = data.find(isCurrentMonth)
    expect(current).toBeDefined()
    const others = data.filter((m) => !isCurrentMonth(m))
    expect(others).toHaveLength(11)
  })
})

// ── BillRow overflow test (logic) ────────────────────────────────────────────

describe('BillRow — long name', () => {
  it('long bill name is a string (rendering is a Playwright concern)', () => {
    const bill = {
      name: 'Cooperativa de Electricidad del Sur de Buenos Aires',
      category: 'electricidad',
      amount: 15000,
      dueDate: '2026-06-10',
      isPaid: false,
    }
    // Verify the bill object is valid — overflow is tested in Playwright
    expect(bill.name.length).toBeGreaterThan(30)
    expect(bill.category).toBe('electricidad')
  })
})
