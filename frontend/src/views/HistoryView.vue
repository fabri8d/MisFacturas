<script setup>
/**
 * Vista de historial — gráfico de barras (Chart.js via CDN) y tabla resumen.
 * Chart.js se carga como script tag para no aumentar el bundle.
 */
import { onMounted, onUnmounted, ref } from 'vue'
import { useBillsStore } from '../stores/bills'

const store = useBillsStore()
const summary = ref([])
const loading = ref(true)
const chartCanvas = ref(null)
let chartInstance = null

const fmt = (n) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(n)

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
  if (!chartCanvas.value || !summary.value.length) return

  chartInstance = new Chart(chartCanvas.value, {
    type: 'bar',
    data: {
      labels: summary.value.map((s) => s.label.split(' ')[0]), // solo mes
      datasets: [
        {
          label: 'Total',
          data: summary.value.map((s) => s.total),
          backgroundColor: '#fbbf24',
          borderRadius: 6,
        },
        {
          label: 'Pagado',
          data: summary.value.map((s) => s.paid),
          backgroundColor: '#4ade80',
          borderRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.dataset.label}: ${fmt(ctx.raw)}`,
          },
        },
      },
      scales: {
        x: { grid: { color: '#26263a' }, ticks: { color: '#6a6860' } },
        y: { display: false },
      },
    },
  })
}

onMounted(async () => {
  loading.value = true
  try {
    summary.value = await store.fetchSummary(6)
    await buildChart()
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  if (chartInstance) chartInstance.destroy()
})
</script>

<template>
  <div>
    <h1 class="page-title">Historial</h1>

    <div v-if="loading" class="loading">Cargando...</div>

    <template v-else>
      <!-- Leyenda custom -->
      <div class="legend">
        <span class="legend-item"><span class="dot" style="background:#fbbf24"></span>Total</span>
        <span class="legend-item"><span class="dot" style="background:#4ade80"></span>Pagado</span>
      </div>

      <!-- Gráfico -->
      <div class="chart-wrap">
        <canvas ref="chartCanvas" />
      </div>

      <!-- Tabla resumen -->
      <section class="mt-24">
        <h2 class="section-title">Resumen mensual</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Mes</th>
                <th>Total</th>
                <th>Pagado</th>
                <th>Pendiente</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in summary" :key="row.month">
                <td class="month-label">{{ row.label }}</td>
                <td>{{ fmt(row.total) }}</td>
                <td class="paid">{{ fmt(row.paid) }}</td>
                <td class="pending">{{ fmt(row.total - row.paid) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.page-title { font-size: 1.5rem; font-weight: 700; margin-bottom: 20px; }
.loading { text-align: center; color: var(--text-muted); padding: 48px; }
.mt-24 { margin-top: 24px; }
.section-title { font-size: 0.85rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px; }

.legend { display: flex; gap: 16px; margin-bottom: 12px; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 0.82rem; color: var(--text-muted); }
.dot { width: 10px; height: 10px; border-radius: 50%; }

.chart-wrap {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
}

.table-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
th { background: var(--surface-2); color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; padding: 10px 14px; text-align: left; }
td { padding: 10px 14px; border-top: 1px solid var(--border); }
.month-label { font-weight: 500; text-transform: capitalize; }
.paid    { color: var(--success); }
.pending { color: var(--danger); }
</style>
