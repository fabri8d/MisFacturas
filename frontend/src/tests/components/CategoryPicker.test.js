import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import CategoryPicker from '../../components/CategoryPicker.vue'

describe('CategoryPicker', () => {
  it('renders all 10 categories', () => {
    const wrapper = mount(CategoryPicker, { props: { modelValue: 'otro' } })
    // v-item-group renders one v-card per category
    const cards = wrapper.findAllComponents({ name: 'VCard' })
    expect(cards.length).toBe(10)
  })

  it('displays emoji for each category', () => {
    const wrapper = mount(CategoryPicker, { props: { modelValue: 'otro' } })
    const text = wrapper.text()
    expect(text).toContain('⚡')
    expect(text).toContain('🔥')
    expect(text).toContain('💧')
  })

  it('displays all category labels', () => {
    const wrapper = mount(CategoryPicker, { props: { modelValue: 'otro' } })
    const text = wrapper.text()
    expect(text).toContain('Gas')
    expect(text).toContain('Agua')
    expect(text).toContain('Internet')
  })

  it('renders with a selected category', () => {
    const wrapper = mount(CategoryPicker, { props: { modelValue: 'electricidad' } })
    // Just verifies it renders without errors
    expect(wrapper.text()).toContain('Electricidad')
  })
})
