<script setup>
/**
 * CategoryPicker — Selector de categoría de factura.
 * @prop {string} modelValue - Clave de categoría seleccionada
 * @emit {string} update:modelValue - Nueva clave seleccionada
 */
import { CATEGORIES, CATEGORY_KEYS } from '../constants/categories'

defineProps({ modelValue: { type: String, default: 'otro' } })
defineEmits(['update:modelValue'])
</script>

<template>
  <div class="picker">
    <button
      v-for="key in CATEGORY_KEYS"
      :key="key"
      type="button"
      class="cat-btn"
      :class="{ active: modelValue === key }"
      :style="modelValue === key ? { borderColor: CATEGORIES[key].color } : {}"
      @click="$emit('update:modelValue', key)"
    >
      <span class="emoji">{{ CATEGORIES[key].emoji }}</span>
      <span class="name">{{ CATEGORIES[key].label }}</span>
    </button>
  </div>
</template>

<style scoped>
.picker {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 8px;
}
.cat-btn {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  font-size: 0.75rem;
  color: var(--text-muted);
  transition: all 0.15s;
}
.cat-btn:hover { background: var(--surface-3); color: var(--text); }
.cat-btn.active { background: var(--surface-3); color: var(--text); font-weight: 600; }
.emoji { font-size: 1.3rem; }
.name  { text-align: center; line-height: 1.2; }
</style>
