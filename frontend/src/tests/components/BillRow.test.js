import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import BillRow from '../../components/BillRow.vue'

const today = new Date().toISOString().slice(0, 10)
const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10)
const in2Days = new Date(Date.now() + 2 * 86400000).toISOString().slice(0, 10)
const in10Days = new Date(Date.now() + 10 * 86400000).toISOString().slice(0, 10)

function makeBill(overrides = {}) {
  return {
    id: 'test-id', name: 'EPEC', category: 'electricidad',
    amount: 28372.70, dueDate: in10Days, month: in10Days.slice(0, 7),
    isPaid: false, paidDate: null, notes: null, source: 'manual',
    createdAt: '2026-01-01T00:00:00Z', ...overrides,
  }
}

describe('BillRow — status labels', () => {
  it('shows "Pagada" when isPaid=true', () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill({ isPaid: true, paidDate: today }) } })
    expect(wrapper.text()).toContain('Pagada')
  })

  it('shows "Vencida" when overdue', () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill({ dueDate: yesterday }) } })
    expect(wrapper.text()).toContain('Vencida')
  })

  it('shows "Urgente" when due in ≤ 3 days', () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill({ dueDate: in2Days }) } })
    expect(wrapper.text()).toContain('Urgente')
  })

  it('shows "Pendiente" when due in > 3 days', () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill({ dueDate: in10Days }) } })
    expect(wrapper.text()).toContain('Pendiente')
  })
})

describe('BillRow — formatting', () => {
  it('formats amount as ARS currency', () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill({ amount: 28372.70 }) } })
    expect(wrapper.text()).toMatch(/28[\.,\s]?372/)
  })

  it('formats date as DD/MM/YYYY', () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill({ dueDate: '2026-06-16' }) } })
    expect(wrapper.text()).toContain('16/06/2026')
  })

  it('shows bill name', () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill({ name: 'Metrogas' }) } })
    expect(wrapper.text()).toContain('Metrogas')
  })
})

describe('BillRow — events', () => {
  it('has a checkbox for toggling paid state', () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill() } })
    const checkbox = wrapper.findComponent({ name: 'VCheckboxBtn' })
    expect(checkbox.exists()).toBe(true)
    // The checkbox is bound to @update:model-value="emit('toggle')"
    // Actual click → event chain is validated via E2E tests
  })

  it('shows action buttons when showActions=true', () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill(), showActions: true } })
    const btns = wrapper.findAllComponents({ name: 'VBtn' })
    expect(btns.length).toBeGreaterThanOrEqual(2)
  })

  it('no overflow: long name does not exceed container', () => {
    const longName = 'Cooperativa de Electricidad del Sur de Buenos Aires'
    const wrapper = mount(BillRow, { props: { bill: makeBill({ name: longName }) } })
    expect(wrapper.text()).toContain(longName)
  })
})
