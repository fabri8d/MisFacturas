<script setup>
/**
 * MonthNav — Navegador de mes con flechas.
 * Lee y escribe currentMonth del store de facturas.
 */
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

<template>
  <div class="month-nav">
    <button @click="shift(-1)" aria-label="Mes anterior">‹</button>
    <span class="label">{{ label }}</span>
    <button @click="shift(1)" aria-label="Mes siguiente">›</button>
  </div>
</template>

<style scoped>
.month-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 8px 0 16px;
}
.label { font-size: 1rem; font-weight: 600; text-transform: capitalize; }
button {
  background: var(--surface-2);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 8px;
  width: 36px;
  height: 36px;
  font-size: 1.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}
button:hover { background: var(--surface-3); }
</style>
