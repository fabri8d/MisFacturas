<template>
  <div class="d-flex align-center justify-center py-3" style="gap:12px">
    <v-btn
      icon="mdi-chevron-left"
      variant="outlined"
      size="small"
      aria-label="Mes anterior"
      @click="shift(-1)"
    />
    <v-chip color="primary" variant="tonal" size="default" class="px-4 font-weight-medium text-capitalize">
      {{ label }}
    </v-chip>
    <v-btn
      icon="mdi-chevron-right"
      variant="outlined"
      size="small"
      aria-label="Mes siguiente"
      @click="shift(1)"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useBillsStore } from '../stores/bills'

const store = useBillsStore()

const MONTHS_ES = [
  'enero','febrero','marzo','abril','mayo','junio',
  'julio','agosto','septiembre','octubre','noviembre','diciembre',
]

const label = computed(() => {
  const [y, m] = store.currentMonth.split('-').map(Number)
  return `${MONTHS_ES[m - 1]} ${y}`
})

function shift(delta) {
  const [y, m] = store.currentMonth.split('-').map(Number)
  const d = new Date(y, m - 1 + delta, 1)
  store.currentMonth = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  store.fetchBills()
}
</script>
