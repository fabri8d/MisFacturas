<template>
  <v-list-item
    rounded="lg"
    border
    class="mb-2 py-2"
    :ripple="false"
  >
    <template #prepend>
      <v-avatar :color="avatarBg" size="38" class="me-2">
        <span style="font-size: 1.1rem">{{ cat.emoji }}</span>
      </v-avatar>
    </template>

    <v-list-item-title class="text-body-2 font-weight-medium">
      {{ bill.name }}
    </v-list-item-title>
    <v-list-item-subtitle class="text-caption">
      {{ fmtDate(bill.dueDate) }}
      <template v-if="bill.notes"> · {{ bill.notes }}</template>
    </v-list-item-subtitle>

    <template #append>
      <div class="d-flex flex-column align-end" style="gap:4px; min-width: 90px">
        <span class="text-body-2 font-weight-bold">{{ fmt(bill.amount) }}</span>
        <v-chip :color="chipColor" variant="tonal" size="x-small">
          {{ status.label }}
        </v-chip>
        <div v-if="showActions" class="d-flex" style="gap:2px; margin-top:2px">
          <v-btn
            icon="mdi-pencil-outline"
            variant="text"
            size="x-small"
            @click.stop="emit('edit')"
          />
          <v-btn
            icon="mdi-delete-outline"
            variant="text"
            size="x-small"
            color="error"
            @click.stop="emit('delete')"
          />
        </div>
      </div>
      <v-checkbox-btn
        :model-value="bill.isPaid"
        color="success"
        class="ms-3 flex-shrink-0"
        hide-details
        @update:model-value="emit('toggle')"
      />
    </template>
  </v-list-item>
</template>

<script setup>
import { computed } from 'vue'
import { CATEGORIES } from '../constants/categories'

const props = defineProps({
  bill:        { type: Object,  required: true },
  showActions: { type: Boolean, default: false },
})
const emit = defineEmits(['toggle', 'edit', 'delete'])

const fmt = (n) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(n)

const fmtDate = (s) => {
  if (!s) return ''
  const [y, m, d] = s.split('-')
  return `${d}/${m}/${y}`
}

const status = computed(() => {
  if (props.bill.isPaid) return { label: 'Pagada', key: 'paid' }
  const today = new Date().toISOString().slice(0, 10)
  if (props.bill.dueDate < today) return { label: 'Vencida', key: 'overdue' }
  const diffDays = Math.ceil((new Date(props.bill.dueDate) - new Date(today)) / 86400000)
  if (diffDays <= 3) return { label: 'Urgente', key: 'urgent' }
  return { label: 'Pendiente', key: 'pending' }
})

const chipColor = computed(() => ({
  paid:    'success',
  overdue: 'error',
  urgent:  'warning',
  pending: 'default',
}[status.value.key]))

const avatarBg = computed(() => ({
  paid:    'success-lighten-4',
  overdue: 'error-lighten-4',
  urgent:  'warning-lighten-4',
  pending: 'surface-variant',
}[status.value.key]))

const cat = computed(() => CATEGORIES[props.bill.category] ?? CATEGORIES.otro)
</script>
