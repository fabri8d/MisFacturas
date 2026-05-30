<template>
  <div>
    <!-- ── Desktop: 2 columnas ──────────────────────────────────────────── -->
    <v-row v-if="mdAndUp" class="desktop-layout">
      <!-- Columna izquierda -->
      <v-col cols="7">
        <MonthNav />
        <div class="d-flex gap-2 mb-3">
          <StatCard label="Total"     :amount="store.totalAmount" />
          <StatCard label="Pagado"    :amount="store.paidAmount"  variant="success" />
          <StatCard label="Pendiente" :amount="store.pendingAmount" variant="danger" />
        </div>
        <ProgressBar :paid="store.paidAmount" :total="store.totalAmount" class="mb-4" />

        <div v-if="store.loading" class="text-center py-8">
          <v-progress-circular indeterminate color="primary" />
        </div>
        <section v-else>
          <div class="text-caption text-medium-emphasis text-uppercase font-weight-semibold mb-2">
            Facturas del mes
          </div>
          <div v-if="store.billsForMonth.length === 0" class="text-body-2 text-medium-emphasis py-4">
            No hay facturas para este mes.
            <router-link to="/bills/new" class="text-primary">Agregar una</router-link>
          </div>
          <v-list v-else lines="two" class="pa-0">
            <BillRow
              v-for="bill in store.billsForMonth"
              :key="bill.id"
              :bill="bill"
              @toggle="handleToggle(bill)"
              @edit="router.push('/bills/' + bill.id)"
              @open-receipts="openReceipts"
            />
          </v-list>
        </section>
      </v-col>

      <!-- Columna derecha (sticky) -->
      <v-col cols="5">
        <div style="position:sticky; top:16px">
          <v-alert
            v-if="store.overdueBills.length"
            type="error"
            variant="tonal"
            rounded="lg"
            class="mb-3 text-body-2"
            :title="`${store.overdueBills.length} vencida${store.overdueBills.length !== 1 ? 's' : ''}`"
          >
            {{ store.overdueBills.map((b) => b.name).join(', ') }}
          </v-alert>

          <!-- Próximas a vencer -->
          <v-card v-if="store.upcomingBills.length" border elevation="0" rounded="lg" class="mb-3">
            <v-card-title class="text-caption text-uppercase text-medium-emphasis pt-3 pb-0 px-4">
              Próximas a vencer
            </v-card-title>
            <v-list lines="two" class="pa-0 px-2 pb-2">
              <BillRow
                v-for="bill in store.upcomingBills.slice(0, 5)"
                :key="bill.id"
                :bill="bill"
                @toggle="handleToggle(bill)"
              />
            </v-list>
          </v-card>

          <!-- Mini breakdown de categorías -->
          <v-card v-if="breakdown.length" border elevation="0" rounded="lg">
            <v-card-title class="text-caption text-uppercase text-medium-emphasis pt-3 pb-0 px-4">
              Por categoría
            </v-card-title>
            <v-card-text class="pa-3">
              <div v-for="row in breakdown" :key="row.key" class="mb-2">
                <div class="d-flex justify-space-between mb-1">
                  <span class="text-caption">{{ row.emoji }} {{ row.label }}</span>
                  <span class="text-caption font-weight-medium">{{ fmt(row.total) }}</span>
                </div>
                <v-progress-linear
                  :model-value="store.totalAmount > 0 ? (row.total / store.totalAmount) * 100 : 0"
                  color="primary"
                  bg-color="surface-variant"
                  rounded
                  height="4"
                />
              </div>
            </v-card-text>
          </v-card>
        </div>
      </v-col>
    </v-row>

    <!-- ── Mobile: layout lineal ────────────────────────────────────────── -->
    <template v-else>
      <MonthNav />
      <div class="d-flex gap-2 mb-3">
        <StatCard label="Total"     :amount="store.totalAmount" />
        <StatCard label="Pagado"    :amount="store.paidAmount"  variant="success" />
        <StatCard label="Pendiente" :amount="store.pendingAmount" variant="danger" />
      </div>
      <ProgressBar :paid="store.paidAmount" :total="store.totalAmount" class="mb-4" />

      <v-alert
        v-if="store.overdueBills.length"
        type="error"
        variant="tonal"
        rounded="lg"
        class="mb-4 text-body-2"
        :title="`${store.overdueBills.length} factura${store.overdueBills.length !== 1 ? 's' : ''} vencida${store.overdueBills.length !== 1 ? 's' : ''}`"
      >
        {{ store.overdueBills.map((b) => b.name).join(', ') }}
      </v-alert>

      <div v-if="store.loading" class="text-center py-8">
        <v-progress-circular indeterminate color="primary" />
      </div>
      <section v-else>
        <div class="text-caption text-medium-emphasis text-uppercase font-weight-semibold mb-2">
          Facturas del mes
        </div>
        <div v-if="store.billsForMonth.length === 0" class="text-body-2 text-medium-emphasis py-4">
          No hay facturas para este mes.
          <router-link to="/bills/new" class="text-primary">Agregar una</router-link>
        </div>
        <v-list v-else lines="two" class="pa-0">
          <BillRow
            v-for="bill in store.billsForMonth"
            :key="bill.id"
            :bill="bill"
            @toggle="handleToggle(bill)"
            @edit="router.push('/bills/' + bill.id)"
          />
        </v-list>
      </section>

      <section v-if="store.upcomingBills.length" class="mt-4">
        <div class="text-caption text-medium-emphasis text-uppercase font-weight-semibold mb-2">
          Próximas a vencer
        </div>
        <v-list lines="two" class="pa-0">
          <BillRow
            v-for="bill in store.upcomingBills.slice(0, 5)"
            :key="bill.id"
            :bill="bill"
            @toggle="handleToggle(bill)"
          />
        </v-list>
      </section>
    </template>

    <ToastNotif v-bind="toast" @close="toast.visible = false" />

    <ReceiptPanel
      v-model="receiptPanelOpen"
      :billId="selectedBill?.id"
      :billName="selectedBill?.name"
      :billDueDate="selectedBill?.dueDate"
      :hasDrive="driveConnected"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import BillRow from '../components/BillRow.vue'
import ReceiptPanel from '../components/ReceiptPanel.vue'
import MonthNav from '../components/MonthNav.vue'
import ProgressBar from '../components/ProgressBar.vue'
import StatCard from '../components/StatCard.vue'
import ToastNotif from '../components/ToastNotif.vue'
import { CATEGORIES } from '../constants/categories'
import { useBillsStore } from '../stores/bills'
import { useReceiptsStore } from '../stores/receipts'

const store = useBillsStore()
const receiptsStore = useReceiptsStore()
const router = useRouter()
const { mdAndUp } = useDisplay()
const toast = ref({ visible: false, message: '', type: 'info' })
const receiptPanelOpen = ref(false)
const selectedBill = ref(null)
const driveConnected = ref(false)

const fmt = (n) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(n)

function showToast(message, type = 'error') {
  toast.value = { visible: true, message, type }
}

onMounted(async () => {
  store.fetchBills()
  receiptsStore.fetchReceiptCounts()
  try {
    const drive = await store.fetchDriveStatus()
    driveConnected.value = drive.connected && !!drive.folder_id
  } catch { /* opcional */ }
})

function openReceipts(bill) {
  selectedBill.value = bill
  receiptPanelOpen.value = true
}

async function handleToggle(bill) {
  try { await store.togglePaid(bill.id) }
  catch (e) { showToast(e.message) }
}

const breakdown = computed(() => {
  const map = {}
  for (const b of store.billsForMonth) {
    if (!map[b.category]) map[b.category] = { total: 0 }
    map[b.category].total += b.amount
  }
  return Object.entries(map)
    .map(([key, v]) => ({ key, ...(CATEGORIES[key] ?? CATEGORIES.otro), ...v }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 6)
})
</script>
