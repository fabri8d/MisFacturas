import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import BillRow from '../../components/BillRow.vue'

const today = new Date().toISOString().slice(0, 10)
const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10)
const in2Days = new Date(Date.now() + 2 * 86400000).toISOString().slice(0, 10)
const in10Days = new Date(Date.now() + 10 * 86400000).toISOString().slice(0, 10)

function makeBill(overrides = {}) {
  return {
    id: 'test-id',
    name: 'EPEC',
    category: 'electricidad',
    amount: 28372.70,
    dueDate: in10Days,
    month: in10Days.slice(0, 7),
    isPaid: false,
    paidDate: null,
    notes: null,
    source: 'manual',
    createdAt: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('BillRow — status badges', () => {
  it('shows "Pagada" badge when isPaid=true', () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill({ isPaid: true, paidDate: today }) } })
    expect(wrapper.text()).toContain('Pagada')
    expect(wrapper.find('.badge.paid').exists()).toBe(true)
  })

  it('shows "Vencida" badge when overdue', () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill({ dueDate: yesterday }) } })
    expect(wrapper.text()).toContain('Vencida')
    expect(wrapper.find('.badge.overdue').exists()).toBe(true)
  })

  it('shows "Urgente" badge when due in ≤ 3 days', () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill({ dueDate: in2Days }) } })
    expect(wrapper.text()).toContain('Urgente')
    expect(wrapper.find('.badge.urgent').exists()).toBe(true)
  })

  it('shows "Pendiente" badge when due in > 3 days', () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill({ dueDate: in10Days }) } })
    expect(wrapper.text()).toContain('Pendiente')
    expect(wrapper.find('.badge.pending').exists()).toBe(true)
  })
})

describe('BillRow — formatting', () => {
  it('formats amount as ARS currency', () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill({ amount: 28372.70 }) } })
    // Intl.NumberFormat es-AR produce $28.372,70 (con posible nbsp)
    const text = wrapper.text()
    expect(text).toMatch(/28[\.,\s]?372/)
  })

  it('formats date as DD/MM/YYYY', () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill({ dueDate: '2026-06-16' }) } })
    expect(wrapper.text()).toContain('16/06/2026')
  })
})

describe('BillRow — events', () => {
  it('emits "toggle" on check button click', async () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill() } })
    await wrapper.find('.check').trigger('click')
    expect(wrapper.emitted('toggle')).toBeTruthy()
  })

  it('emits "edit" on edit button click when showActions=true', async () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill(), showActions: true } })
    await wrapper.find('.icon-btn:not(.danger)').trigger('click')
    expect(wrapper.emitted('edit')).toBeTruthy()
  })

  it('emits "delete" on delete button click when showActions=true', async () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill(), showActions: true } })
    await wrapper.find('.icon-btn.danger').trigger('click')
    expect(wrapper.emitted('delete')).toBeTruthy()
  })

  it('does not show action buttons when showActions=false', () => {
    const wrapper = mount(BillRow, { props: { bill: makeBill(), showActions: false } })
    expect(wrapper.find('.actions').exists()).toBe(false)
  })
})
