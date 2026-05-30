<template>
  <div>
    <!-- Header con navegación de año -->
    <div class="d-flex align-center justify-space-between mb-4">
      <h1 class="text-h5 font-weight-bold" style="font-family: var(--font-display)">Historial</h1>
      <div class="d-flex align-center" style="gap:8px">
        <v-btn icon="mdi-chevron-left" variant="text" size="small" @click="prevYear" />
        <span class="text-h6 font-weight-bold" style="min-width:60px;text-align:center">
          {{ store.summaryYear }}
        </span>
        <v-btn
          icon="mdi-chevron-right"
          variant="text"
          size="small"
          :disabled="store.summaryYear >= currentYear"
          @click="nextYear"
        />
      </div>
    </div>

    <div v-if="loading" class="text-center py-8">
      <v-progress-circular indeterminate color="primary" />
    </div>

    <template v-else>
      <!-- Totales del año -->
      <v-row class="mb-4" dense>
        <v-col cols="4">
          <v-card border elevation="0" rounded="lg" class="pa-3 text-center">
            <div class="text-caption text-uppercase text-medium-emphasis mb-1">Total</div>
            <div class="text-body-2 font-weight-bold" style="font-family:var(--font-display)">
              {{ fmtShort(yearTotal) }}
            </div>
          </v-card>
        </v-col>
        <v-col cols="4">
          <v-card border elevation="0" rounded="lg" class="pa-3 text-center">
            <div class="text-caption text-uppercase text-medium-emphasis mb-1">Pagado</div>
            <div class="text-body-2 font-weight-bold text-success" style="font-family:var(--font-display)">
              {{ fmtShort(yearPaid) }}
            </div>
          </v-card>
        </v-col>
        <v-col cols="4">
          <v-card border elevation="0" rounded="lg" class="pa-3 text-center">
            <div class="text-caption text-uppercase text-medium-emphasis mb-1">Pendiente</div>
            <div class="text-body-2 font-weight-bold text-error" style="font-family:var(--font-display)">
              {{ fmtShort(yearPending) }}
            </div>
          </v-card>
        </v-col>
      </v-row>

      <!-- Gráfico apilado -->
      <v-card border elevation="0" rounded="lg" class="mb-4 pa-4">
        <div :style="{ height: chartHeight + 'px', position: 'relative' }">
          <canvas id="historyChart" />
        </div>
      </v-card>

      <!-- Tabla de 12 meses -->
      <v-card border elevation="0" rounded="lg">
        <v-card-title class="text-caption text-uppercase text-medium-emphasis pt-3 pb-0 px-4">
          Resumen {{ store.summaryYear }}
        </v-card-title>
        <v-table density="compact">
          <thead>
            <tr>
              <th class="text-caption text-uppercase">Mes</th>
              <th class="text-caption text-uppercase text-end">Total</th>
              <th class="text-caption text-uppercase text-end">Pagado</th>
              <th class="text-caption text-uppercase text-end">Pendiente</th>
              <th class="text-caption text-uppercase text-center">%</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in summaryData"
              :key="row.month"
              :class="{ 'current-month-row': isCurrentMonth(row) }"
            >
              <td
                class="text-body-2 text-capitalize"
                :class="row.total === 0 ? 'text-medium-emphasis' : 'font-weight-medium'"
              >
                {{ row.label }}
              </td>
              <td class="text-body-2 text-end" :class="row.total === 0 ? 'text-medium-emphasis' : ''">
                {{ row.total > 0 ? fmt(row.total) : '—' }}
              </td>
              <td class="text-body-2 text-end" :class="row.paid > 0 ? 'text-success' : 'text-medium-emphasis'">
                {{ row.paid > 0 ? fmt(row.paid) : '—' }}
              </td>
              <td class="text-body-2 text-end" :class="(row.total - row.paid) > 0 ? 'text-error' : 'text-medium-emphasis'">
                {{ (row.total - row.paid) > 0 ? fmt(row.total - row.paid) : '—' }}
              </td>
              <td class="text-caption text-center text-medium-emphasis">
                {{ row.total > 0 ? Math.round((row.paid / row.total) * 100) + '%' : '—' }}
              </td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="bg-surface-variant">
              <td class="text-body-2 font-weight-bold">Total {{ store.summaryYear }}</td>
              <td class="text-body-2 font-weight-bold text-end">{{ fmt(yearTotal) }}</td>
              <td class="text-body-2 font-weight-bold text-success text-end">{{ fmt(yearPaid) }}</td>
              <td class="text-body-2 font-weight-bold text-error text-end">{{ fmt(yearPending) }}</td>
              <td class="text-body-2 font-weight-bold text-center">
                {{ yearTotal > 0 ? Math.round((yearPaid / yearTotal) * 100) + '%' : '—' }}
              </td>
            </tr>
          </tfoot>
        </v-table>
      </v-card>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useDisplay } from 'vuetify'
import { useBillsStore } from '../stores/bills'

const store = useBillsStore()
const { mdAndUp } = useDisplay()
const summaryData = ref([])
const loading = ref(true)

const currentYear = new Date().getFullYear()

const fmt = (n) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(n)

const fmtShort = (n) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 }).format(n)

const fmtARS = (n) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 }).format(n)

const chartHeight = computed(() => (mdAndUp.value ? 400 : 240))

const yearTotal   = computed(() => summaryData.value.reduce((s, m) => s + m.total, 0))
const yearPaid    = computed(() => summaryData.value.reduce((s, m) => s + m.paid, 0))
const yearPending = computed(() => yearTotal.value - yearPaid.value)

function isCurrentMonth(row) {
  const now = new Date()
  const cm = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  return row.month === cm
}

// ── Chart ──────────────────────────────────────────────────────────────────

let chartInstance = null

function loadChartJs() {
  return new Promise((resolve, reject) => {
    if (window.Chart) return resolve(window.Chart)
    const s = document.createElement('script')
    s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js'
    s.onload = () => resolve(window.Chart)
    s.onerror = reject
    document.head.appendChild(s)
  })
}

async function buildChart() {
  const Chart = await loadChartJs()
  if (chartInstance) { chartInstance.destroy(); chartInstance = null }
  const ctx = document.getElementById('historyChart')
  if (!ctx || !summaryData.value.length) return

  chartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: summaryData.value.map((m) => m.label),
      datasets: [
        {
          label: 'Pagado',
          data: summaryData.value.map((m) => m.paid),
          backgroundColor: '#00897B',
          stack: 'bills',
          borderRadius: { topLeft: 0, topRight: 0, bottomLeft: 4, bottomRight: 4 },
        },
        {
          label: 'Pendiente',
          data: summaryData.value.map((m) => m.total - m.paid),
          backgroundColor: '#B2DFDB',
          stack: 'bills',
          borderRadius: { topLeft: 4, topRight: 4, bottomLeft: 0, bottomRight: 0 },
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16, font: { size: 12 } } },
        tooltip: {
          callbacks: {
            title: (items) => items[0].label,
            label: (item) => ` ${item.dataset.label}: ${fmtARS(item.raw)}`,
            footer: (items) => {
              const total = items.reduce((s, i) => s + i.raw, 0)
              return `Total: ${fmtARS(total)}`
            },
          },
        },
      },
      scales: {
        x: {
          stacked: true,
          grid: { display: false },
          ticks: { font: { size: 11 }, color: '#9e9e9e' },
        },
        y: {
          stacked: true,
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: {
            callback: (val) => fmtARS(val),
            maxTicksLimit: 6,
            font: { size: 10 },
            color: '#9e9e9e',
          },
        },
      },
    },
  })
}

// ── Year navigation ────────────────────────────────────────────────────────

async function loadYear(year) {
  loading.value = true
  try {
    summaryData.value = await store.fetchSummary(year)
  } finally {
    loading.value = false
  }
  // loading=false primero → Vue renderiza el canvas → luego dibujamos
  await nextTick()
  await buildChart()
}

function prevYear() { store.setSummaryYear(store.summaryYear - 1) }
function nextYear() {
  if (store.summaryYear < currentYear) store.setSummaryYear(store.summaryYear + 1)
}

watch(() => store.summaryYear, (year) => loadYear(year))
watch(mdAndUp, () => nextTick(() => buildChart()))

onMounted(() => loadYear(store.summaryYear))
onBeforeUnmount(() => { if (chartInstance) chartInstance.destroy() })
</script>

<style scoped>
.current-month-row {
  background: rgba(0, 137, 123, 0.06);
}
</style>
