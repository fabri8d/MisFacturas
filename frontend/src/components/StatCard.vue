<template>
  <v-card :elevation="0" border rounded="lg" class="flex-1 pa-3">
    <div class="text-caption text-medium-emphasis text-uppercase font-weight-medium mb-1">
      {{ label }}
    </div>
    <div
      class="font-weight-bold"
      :class="amountClass"
      style="font-size: clamp(0.85rem, 3.5vw, 1.2rem); overflow: hidden; text-overflow: ellipsis; white-space: nowrap"
    >
      {{ fmt(amount) }}
    </div>
  </v-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label:   { type: String, required: true },
  amount:  { type: Number, required: true },
  variant: { type: String, default: 'default' },
})

const fmt = (n) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(n)

const amountClass = computed(() => ({
  'text-success': props.variant === 'success',
  'text-error':   props.variant === 'danger',
  'text-warning': props.variant === 'warning',
}))
</script>
