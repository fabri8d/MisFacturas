import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import CategoryPicker from '../../components/CategoryPicker.vue'

describe('CategoryPicker', () => {
  it('renders all 10 categories', () => {
    const wrapper = mount(CategoryPicker, { props: { modelValue: 'otro' } })
    expect(wrapper.findAll('.cat-btn').length).toBe(10)
  })

  it('marks selected category as active', () => {
    const wrapper = mount(CategoryPicker, { props: { modelValue: 'gas' } })
    const active = wrapper.findAll('.cat-btn.active')
    expect(active.length).toBe(1)
    expect(active[0].text()).toContain('Gas')
  })

  it('emits update:modelValue on category click', async () => {
    const wrapper = mount(CategoryPicker, { props: { modelValue: 'otro' } })
    const btns = wrapper.findAll('.cat-btn')
    await btns[0].trigger('click') // electricidad
    expect(wrapper.emitted('update:modelValue')?.[0]?.[0]).toBe('electricidad')
  })

  it('displays emoji for each category', () => {
    const wrapper = mount(CategoryPicker, { props: { modelValue: 'otro' } })
    const text = wrapper.text()
    expect(text).toContain('⚡')
    expect(text).toContain('🔥')
    expect(text).toContain('💧')
  })
})
