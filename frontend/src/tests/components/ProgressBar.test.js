import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ProgressBar from '../../components/ProgressBar.vue'

describe('ProgressBar', () => {
  it('sets width to correct percentage', () => {
    const wrapper = mount(ProgressBar, { props: { paid: 75, total: 100 } })
    expect(wrapper.find('.bar-fill').attributes('style')).toContain('75%')
  })

  it('clamps width at 100% when paid > total', () => {
    const wrapper = mount(ProgressBar, { props: { paid: 150, total: 100 } })
    expect(wrapper.find('.bar-fill').attributes('style')).toContain('100%')
  })

  it('shows 0% when paid=0', () => {
    const wrapper = mount(ProgressBar, { props: { paid: 0, total: 100 } })
    expect(wrapper.find('.bar-fill').attributes('style')).toContain('0%')
  })

  it('shows 0% when total=0 (no division by zero)', () => {
    const wrapper = mount(ProgressBar, { props: { paid: 0, total: 0 } })
    expect(wrapper.find('.bar-fill').attributes('style')).toContain('0%')
  })

  it('displays percentage label', () => {
    const wrapper = mount(ProgressBar, { props: { paid: 25, total: 100 } })
    expect(wrapper.text()).toContain('25%')
  })
})
