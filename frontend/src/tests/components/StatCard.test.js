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

  it('applies text-success class for success variant', () => {
    const wrapper = mount(StatCard, { props: { label: 'X', amount: 0, variant: 'success' } })
    expect(wrapper.html()).toContain('text-success')
  })

  it('applies text-error class for danger variant', () => {
    const wrapper = mount(StatCard, { props: { label: 'X', amount: 0, variant: 'danger' } })
    expect(wrapper.html()).toContain('text-error')
  })

  it('no color class for default variant', () => {
    const wrapper = mount(StatCard, { props: { label: 'X', amount: 0 } })
    const html = wrapper.html()
    expect(html).not.toContain('text-success')
    expect(html).not.toContain('text-error')
  })
})
