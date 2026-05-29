<script setup>
/** Vista de facturas — lista completa del mes con desglose por categoría. */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import BillRow from '../components/BillRow.vue'
import MonthNav from '../components/MonthNav.vue'
import ToastNotif from '../components/ToastNotif.vue'
import { CATEGORIES } from '../constants/categories'
import { useBillsStore } from '../stores/bills'

const store = useBillsStore()
const router = useRouter()
const toast = ref({ visible: false, message: '', type: 'info' })

const fmt = (n) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(n)

function showToast(message, type = 'error') {
  toast.value = { visible: true, message, type }
}

onMounted(() => store.fetchBills())

async function handleToggle(bill) {
  try { await store.togglePaid(bill.id) }
  catch (e) { showToast(e.message) }
}

async function handleDelete(bill) {
  if (!confirm(`¿Eliminar "${bill.name}"?\nEsta acción no se puede deshacer.`)) return
  try {
    await store.deleteBill(bill.id)
    showToast('Factura eliminada', 'success')
    await store.fetchBills()
  } catch (e) {
    showToast(e.message)
  }
}

/** Desglose de categorías para el mes actual */
const breakdown = computed(() => {
  const map = {}
  for (const b of store.billsForMonth) {
    if (!map[b.category]) map[b.category] = { count: 0, total: 0 }
    map[b.category].count++
    map[b.category].total += b.amount
  }
  return Object.entries(map).map(([key, v]) => ({
    key,
    ...CATEGORIES[key] ?? CATEGORIES.otro,
    ...v,
  }))
})
</script>

<template>
  <div>
    <div class="header">
      <h1 class="page-title">Facturas</h1>
      <router-link to="/bills/new" class="add-btn">+ Nueva</router-link>
    </div>

    <MonthNav />

    <div v-if="store.loading" class="loading">Cargando...</div>

    <div v-else class="list">
      <BillRow
        v-for="bill in store.billsForMonth"
        :key="bill.id"
        :bill="bill"
        :show-actions="true"
        @toggle="handleToggle(bill)"
        @edit="router.push('/bills/' + bill.id)"
        @delete="handleDelete(bill)"
      />
      <div v-if="store.billsForMonth.length === 0" class="empty">
        No hay facturas para este mes.
      </div>
    </div>

    <!-- Desglose por categoría -->
    <section v-if="breakdown.length" class="mt-24">
      <h2 class="section-title">Por categoría</h2>
      <div class="breakdown">
        <div v-for="row in breakdown" :key="row.key" class="breakdown-row">
          <span class="emoji">{{ row.emoji }}</span>
          <span class="cat-name">{{ row.label }}</span>
          <span class="count">{{ row.count }} factura{{ row.count !== 1 ? 's' : '' }}</span>
          <span class="subtotal">{{ fmt(row.total) }}</span>
        </div>
        <div class="breakdown-row total-row">
          <span />
          <span class="cat-name">Total</span>
          <span />
          <span class="subtotal">{{ fmt(store.totalAmount) }}</span>
        </div>
      </div>
    </section>

    <ToastNotif v-bind="toast" @close="toast.visible = false" />
  </div>
</template>

<style scoped>
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.page-title { font-size: 1.5rem; font-weight: 700; }
.add-btn {
  background: var(--accent); color: #000;
  padding: 8px 14px; border-radius: var(--radius);
  font-size: 0.85rem; font-weight: 600;
}
.list { display: flex; flex-direction: column; gap: 8px; }
.loading, .empty { text-align: center; color: var(--text-muted); padding: 24px; }
.mt-24 { margin-top: 24px; }
.section-title { font-size: 0.85rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px; }

.breakdown { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
.breakdown-row {
  display: grid;
  grid-template-columns: 28px 1fr auto auto;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  font-size: 0.875rem;
}
.breakdown-row:last-child { border-bottom: none; }
.emoji { font-size: 1.1rem; }
.count { color: var(--text-muted); font-size: 0.8rem; }
.subtotal { font-weight: 600; }
.total-row { background: var(--surface-2); }
.total-row .cat-name, .total-row .subtotal { font-weight: 700; }
</style>
