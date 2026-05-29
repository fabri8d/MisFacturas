import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import StatCard from '../../components/StatCard.vue'

describe('StatCard', () => {
  it('renders label', () => {
    const wrapper = mount(StatCard, { props: { label: 'Total', amount: 1000 } })
    expect(wrapper.text()).toContain('Total')
  })

  it('renders formatted amount', () => {
    const wrapper = mount(StatCard, { props: { label: 'X', amount: 5000 } })
    expect(wrapper.text()).toMatch(/5[\.,\s]?000/)
  })

  it('applies success variant class', () => {
    const wrapper = mount(StatCard, { props: { label: 'X', amount: 0, variant: 'success' } })
    expect(wrapper.find('.stat-card').classes()).toContain('success')
  })

  it('applies danger variant class', () => {
    const wrapper = mount(StatCard, { props: { label: 'X', amount: 0, variant: 'danger' } })
    expect(wrapper.find('.stat-card').classes()).toContain('danger')
  })

  it('defaults to no variant class', () => {
    const wrapper = mount(StatCard, { props: { label: 'X', amount: 0 } })
    const classes = wrapper.find('.stat-card').classes()
    expect(classes).not.toContain('success')
    expect(classes).not.toContain('danger')
  })
})
