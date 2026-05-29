<script setup>
/** Vista de inicio — resumen del mes con stats, progreso, alertas y listas. */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import BillRow from '../components/BillRow.vue'
import MonthNav from '../components/MonthNav.vue'
import ProgressBar from '../components/ProgressBar.vue'
import StatCard from '../components/StatCard.vue'
import ToastNotif from '../components/ToastNotif.vue'
import { useBillsStore } from '../stores/bills'

const store = useBillsStore()
const router = useRouter()
const toast = ref({ visible: false, message: '', type: 'info' })
const driveOk = ref(false)
const telegramOk = ref(false)

function showToast(message, type = 'error') {
  toast.value = { visible: true, message, type }
}

onMounted(async () => {
  store.fetchBills()
  try {
    const [drive, notif] = await Promise.all([
      store.fetchDriveStatus(),
      store.fetchNotificationsConfig(),
    ])
    driveOk.value = drive.connected && !!drive.folder_id
    telegramOk.value = notif.telegram_configured
  } catch { /* chips opcionales, silencioso */ }
})

async function handleToggle(bill) {
  try {
    await store.togglePaid(bill.id)
  } catch (e) {
    showToast(e.message)
  }
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">MisFacturas</h1>
      <div class="status-chips">
        <span v-if="driveOk" class="chip-ok">Drive ✓</span>
        <span v-if="telegramOk" class="chip-ok">Telegram ✓</span>
      </div>
    </div>
    <MonthNav />

    <!-- Stats -->
    <div class="stats-row">
      <StatCard label="Total"     :amount="store.totalAmount" />
      <StatCard label="Pagado"    :amount="store.paidAmount"  variant="success" />
      <StatCard label="Pendiente" :amount="store.pendingAmount" variant="danger" />
    </div>

    <ProgressBar :paid="store.paidAmount" :total="store.totalAmount" class="mt-16" />

    <!-- Banner vencidas -->
    <div v-if="store.overdueBills.length" class="overdue-banner mt-16">
      <strong>⚠️ Facturas vencidas:</strong>
      {{ store.overdueBills.map(b => b.name).join(', ') }}
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="loading">Cargando...</div>

    <!-- Facturas del mes -->
    <section class="mt-24">
      <h2 class="section-title">Facturas del mes</h2>
      <div v-if="!store.loading && store.billsForMonth.length === 0" class="empty">
        No hay facturas para este mes.
        <router-link to="/bills/new" class="link">Agregar una</router-link>
      </div>
      <div class="list">
        <BillRow
          v-for="bill in store.billsForMonth"
          :key="bill.id"
          :bill="bill"
          @toggle="handleToggle(bill)"
          @edit="router.push('/bills/' + bill.id)"
        />
      </div>
    </section>

    <!-- Próximas a vencer -->
    <section v-if="store.upcomingBills.length" class="mt-24">
      <h2 class="section-title">Próximas a vencer</h2>
      <div class="list">
        <BillRow
          v-for="bill in store.upcomingBills.slice(0, 5)"
          :key="bill.id"
          :bill="bill"
          @toggle="handleToggle(bill)"
        />
      </div>
    </section>

    <ToastNotif v-bind="toast" @close="toast.visible = false" />
  </div>
</template>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.page-title  { font-size: 1.5rem; font-weight: 700; }
.status-chips { display: flex; gap: 6px; }
.chip-ok {
  font-size: 0.65rem; font-weight: 600; padding: 3px 8px;
  border-radius: 99px;
  background: rgba(74,222,128,0.12);
  color: var(--success);
  border: 1px solid rgba(74,222,128,0.25);
}
.stats-row  { display: flex; gap: 10px; }
.mt-16 { margin-top: 16px; }
.mt-24 { margin-top: 24px; }
.section-title { font-size: 0.85rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px; }
.list { display: flex; flex-direction: column; gap: 8px; }
.loading { text-align: center; color: var(--text-muted); padding: 24px; }
.empty { color: var(--text-muted); font-size: 0.9rem; padding: 16px 0; }
.link { color: var(--accent-light); }
.overdue-banner {
  background: rgba(248,113,113,0.1);
  border: 1px solid rgba(248,113,113,0.3);
  border-radius: var(--radius);
  padding: 12px 16px;
  font-size: 0.85rem;
  color: var(--danger);
}
</style>
