<template>
  <div>
    <MonthNav />

    <div v-if="store.loading" class="text-center py-8">
      <v-progress-circular indeterminate color="primary" />
    </div>

    <template v-else>
      <!-- ── Desktop: data table ──────────────────────────────────────── -->
      <v-data-table
        v-if="mdAndUp"
        :headers="headers"
        :items="store.billsForMonth"
        :items-per-page="50"
        density="compact"
        class="mb-4"
        no-data-text="No hay facturas para este mes"
      >
        <template #item.category="{ item }">
          <span>{{ CATEGORIES[item.category]?.emoji }} {{ CATEGORIES[item.category]?.label }}</span>
        </template>
        <template #item.amount="{ item }">
          <span class="font-weight-medium">{{ fmt(item.amount) }}</span>
        </template>
        <template #item.dueDate="{ item }">
          {{ fmtDate(item.dueDate) }}
        </template>
        <template #item.status="{ item }">
          <v-chip :color="statusColor(item)" variant="tonal" size="x-small">
            {{ statusLabel(item) }}
          </v-chip>
        </template>
        <template #item.actions="{ item }">
          <v-btn
            icon="mdi-pencil-outline"
            variant="text"
            size="x-small"
            @click="router.push('/bills/' + item.id)"
          />
          <v-btn
            icon="mdi-delete-outline"
            variant="text"
            size="x-small"
            color="error"
            @click="handleDelete(item)"
          />
          <v-checkbox-btn
            :model-value="item.isPaid"
            color="success"
            hide-details
            density="compact"
            @update:model-value="handleToggle(item)"
          />
        </template>
      </v-data-table>

      <!-- ── Mobile: lista ────────────────────────────────────────────── -->
      <template v-else>
        <v-list v-if="store.billsForMonth.length" lines="two" class="pa-0 mb-4">
          <BillRow
            v-for="bill in store.billsForMonth"
            :key="bill.id"
            :bill="bill"
            :show-actions="true"
            @toggle="handleToggle(bill)"
            @edit="router.push('/bills/' + bill.id)"
            @delete="handleDelete(bill)"
          />
        </v-list>
        <div v-else class="text-body-2 text-medium-emphasis py-4 text-center">
          No hay facturas para este mes.
        </div>

        <!-- Desglose por categoría (mobile) -->
        <v-card v-if="breakdown.length" border elevation="0" rounded="lg" class="mt-2">
          <v-card-title class="text-caption text-uppercase text-medium-emphasis pt-3 pb-0 px-4">
            Por categoría
          </v-card-title>
          <v-table density="compact">
            <tbody>
              <tr v-for="row in breakdown" :key="row.key">
                <td class="text-body-2" style="width:28px">{{ row.emoji }}</td>
                <td class="text-body-2">{{ row.label }}</td>
                <td class="text-caption text-medium-emphasis">
                  {{ row.count }} factura{{ row.count !== 1 ? 's' : '' }}
                </td>
                <td class="text-body-2 font-weight-medium text-end">{{ fmt(row.total) }}</td>
              </tr>
              <tr class="bg-surface-variant">
                <td /><td class="text-body-2 font-weight-bold">Total</td>
                <td />
                <td class="text-body-2 font-weight-bold text-end">{{ fmt(store.totalAmount) }}</td>
              </tr>
            </tbody>
          </v-table>
        </v-card>
      </template>
    </template>

    <!-- FAB -->
    <v-btn
      icon="mdi-plus"
      color="primary"
      size="large"
      position="fixed"
      location="bottom end"
      :style="{ marginBottom: mdAndUp ? '16px' : '72px', marginRight: '16px' }"
      elevation="3"
      to="/bills/new"
    />

    <ToastNotif v-bind="toast" @close="toast.visible = false" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import BillRow from '../components/BillRow.vue'
import MonthNav from '../components/MonthNav.vue'
import ToastNotif from '../components/ToastNotif.vue'
import { CATEGORIES } from '../constants/categories'
import { useBillsStore } from '../stores/bills'

const store = useBillsStore()
const router = useRouter()
const { mdAndUp } = useDisplay()
const toast = ref({ visible: false, message: '', type: 'info' })

const fmt = (n) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(n)

const fmtDate = (s) => {
  if (!s) return ''
  const [y, m, d] = s.split('-')
  return `${d}/${m}/${y}`
}

function statusLabel(bill) {
  if (bill.isPaid) return 'Pagada'
  const today = new Date().toISOString().slice(0, 10)
  if (bill.dueDate < today) return 'Vencida'
  const diff = Math.ceil((new Date(bill.dueDate) - new Date(today)) / 86400000)
  return diff <= 3 ? 'Urgente' : 'Pendiente'
}

function statusColor(bill) {
  const s = statusLabel(bill)
  return { Pagada: 'success', Vencida: 'error', Urgente: 'warning', Pendiente: 'default' }[s]
}

const headers = [
  { title: 'Categoría', key: 'category', width: '150px' },
  { title: 'Nombre', key: 'name' },
  { title: 'Monto', key: 'amount', align: 'end', width: '130px' },
  { title: 'Vencimiento', key: 'dueDate', width: '130px' },
  { title: 'Estado', key: 'status', sortable: false, width: '110px' },
  { title: '', key: 'actions', sortable: false, width: '110px', align: 'center' },
]

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
  } catch (e) {
    showToast(e.message)
  }
}

const breakdown = computed(() => {
  const map = {}
  for (const b of store.billsForMonth) {
    if (!map[b.category]) map[b.category] = { count: 0, total: 0 }
    map[b.category].count++
    map[b.category].total += b.amount
  }
  return Object.entries(map).map(([key, v]) => ({
    key, ...(CATEGORIES[key] ?? CATEGORIES.otro), ...v,
  }))
})
</script>
