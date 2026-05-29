import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MonthNav from '../../components/MonthNav.vue'

// Mock del store para aislar el componente
vi.mock('../../stores/bills', () => ({
  useBillsStore: () => ({
    currentMonth: '2026-06',
    fetchBills: vi.fn(),
  }),
}))

describe('MonthNav', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('displays month label', () => {
    const wrapper = mount(MonthNav)
    expect(wrapper.text()).toContain('junio')
    expect(wrapper.text()).toContain('2026')
  })

  it('has prev and next arrow buttons', () => {
    const wrapper = mount(MonthNav)
    const btns = wrapper.findAll('button')
    expect(btns.length).toBe(2)
    expect(btns[0].text()).toContain('‹')
    expect(btns[1].text()).toContain('›')
  })
})
