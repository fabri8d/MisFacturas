<template>
  <div>
    <div class="d-flex justify-space-between mb-1">
      <span class="text-caption text-medium-emphasis">Pagado</span>
      <span class="text-caption text-medium-emphasis">{{ pct }}%</span>
    </div>
    <v-progress-linear
      :model-value="pct"
      color="success"
      bg-color="surface-variant"
      rounded
      height="8"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  paid:  { type: Number, required: true },
  total: { type: Number, required: true },
})

const pct = computed(() =>
  props.total > 0 ? Math.min(100, Math.round((props.paid / props.total) * 100)) : 0
)
</script>
