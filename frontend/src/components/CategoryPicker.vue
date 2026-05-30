<template>
  <v-item-group :model-value="modelValue" mandatory @update:model-value="emit('update:modelValue', $event)">
    <div class="category-grid">
      <v-item v-for="key in CATEGORY_KEYS" :key="key" :value="key" v-slot="{ isSelected, toggle }">
        <v-card
          class="cat-card text-center pa-2"
          :color="isSelected ? 'primary' : undefined"
          :variant="isSelected ? 'tonal' : 'outlined'"
          :elevation="0"
          rounded="lg"
          @click="toggle"
        >
          <div style="font-size:1.3rem">{{ CATEGORIES[key].emoji }}</div>
          <div class="text-caption mt-1" style="line-height:1.2">{{ CATEGORIES[key].label }}</div>
        </v-card>
      </v-item>
    </div>
  </v-item-group>
</template>

<script setup>
import { CATEGORIES, CATEGORY_KEYS } from '../constants/categories'

defineProps({ modelValue: { type: String, default: 'otro' } })
const emit = defineEmits(['update:modelValue'])
</script>

<style scoped>
.category-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(88px, 1fr));
  gap: 8px;
}
.cat-card { cursor: pointer; }
</style>
