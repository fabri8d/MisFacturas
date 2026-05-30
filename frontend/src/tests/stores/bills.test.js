import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// Mock del cliente HTTP
vi.mock('../../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    patch: vi.fn(),
  },
}))

import client from '../../api/client'
import { useBillsStore } from '../../stores/bills'

const today = new Date().toISOString().slice(0, 10)
const thisMonth = today.slice(0, 7)
const in2Days = new Date(Date.now() + 2 * 86400000).toISOString().slice(0, 10)
const in10Days = new Date(Date.now() + 10 * 86400000).toISOString().slice(0, 10)
const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10)

function makeBill(overrides = {}) {
  return {
    id: 'bill-1',
    name: 'EPEC',
    category: 'electricidad',
    amount: 1000,
    dueDate: in10Days,
    month: thisMonth,
    isPaid: false,
    paidDate: null,
    notes: null,
    source: 'manual',
    createdAt: new Date().toISOString(),
    ...overrides,
  }
}

describe('bills store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchBills populates state', async () => {
    const bill = makeBill()
    client.get.mockResolvedValue([bill])

    const store = useBillsStore()
    store.currentMonth = thisMonth
    await store.fetchBills()

    expect(store.bills).toHaveLength(1)
    expect(store.bills[0].id).toBe('bill-1')
  })

  it('createBill adds to state', async () => {
    const newBill = makeBill({ id: 'new-id' })
    client.post.mockResolvedValue(newBill)
    // fetchBills() called after create — mock to return the new bill
    client.get.mockResolvedValue([newBill])

    const store = useBillsStore()
    await store.createBill({ name: 'EPEC', amount: 1000, dueDate: in10Days, category: 'electricidad' })

    expect(store.bills).toHaveLength(1)
    expect(store.bills[0].id).toBe('new-id')
  })

  it('deleteBill removes from state', async () => {
    const store = useBillsStore()
    store.bills = [makeBill({ id: 'del-id' })]
    client.delete.mockResolvedValue(undefined)
    // fetchBills() called after delete — mock to return empty
    client.get.mockResolvedValue([])

    await store.deleteBill('del-id')
    expect(store.bills).toHaveLength(0)
  })

  it('togglePaid updates bill in state', async () => {
    const store = useBillsStore()
    store.bills = [makeBill({ id: 'tog-id', isPaid: false })]
    client.patch.mockResolvedValue(makeBill({ id: 'tog-id', isPaid: true, paidDate: today }))

    await store.togglePaid('tog-id')
    expect(store.bills[0].isPaid).toBe(true)
  })

  // ── Getters ─────────────────────────────────────────────────────────────

  it('billsForMonth filters by currentMonth', () => {
    const store = useBillsStore()
    store.currentMonth = thisMonth
    store.bills = [
      makeBill({ month: thisMonth }),
      makeBill({ id: 'other', month: '2025-01' }),
    ]
    expect(store.billsForMonth).toHaveLength(1)
  })

  it('totalAmount sums all bills for current month', () => {
    const store = useBillsStore()
    store.currentMonth = thisMonth
    store.bills = [
      makeBill({ amount: 1000, month: thisMonth }),
      makeBill({ id: 'b2', amount: 500, month: thisMonth }),
    ]
    expect(store.totalAmount).toBe(1500)
  })

  it('paidAmount sums only isPaid=true bills', () => {
    const store = useBillsStore()
    store.currentMonth = thisMonth
    store.bills = [
      makeBill({ amount: 1000, isPaid: true, month: thisMonth }),
      makeBill({ id: 'b2', amount: 500, isPaid: false, month: thisMonth }),
    ]
    expect(store.paidAmount).toBe(1000)
    expect(store.pendingAmount).toBe(500)
  })

  it('overdueBills returns only unpaid past-due bills', () => {
    const store = useBillsStore()
    store.currentMonth = thisMonth
    store.bills = [
      makeBill({ id: 'overdue', dueDate: yesterday, isPaid: false, month: thisMonth }),
      makeBill({ id: 'paid', dueDate: yesterday, isPaid: true, month: thisMonth }),
      makeBill({ id: 'future', dueDate: in10Days, isPaid: false, month: thisMonth }),
    ]
    const overdue = store.overdueBills
    expect(overdue).toHaveLength(1)
    expect(overdue[0].id).toBe('overdue')
  })

  it('upcomingBills returns unpaid bills due within 7 days, sorted by dueDate', () => {
    const store = useBillsStore()
    store.currentMonth = thisMonth
    store.bills = [
      makeBill({ id: 'urgent', dueDate: in2Days, isPaid: false, month: thisMonth }),
      makeBill({ id: 'far', dueDate: in10Days, isPaid: false, month: thisMonth }),
      makeBill({ id: 'paid-upcoming', dueDate: in2Days, isPaid: true, month: thisMonth }),
    ]
    const upcoming = store.upcomingBills
    expect(upcoming.map(b => b.id)).toContain('urgent')
    expect(upcoming.map(b => b.id)).not.toContain('far')
    expect(upcoming.map(b => b.id)).not.toContain('paid-upcoming')
  })
})
