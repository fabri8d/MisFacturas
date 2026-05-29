<script setup>
/**
 * Vista de ajustes — sección Datos: contador, exportar e importar facturas.
 */
import { onMounted, ref } from 'vue'
import ToastNotif from '../components/ToastNotif.vue'
import { useBillsStore } from '../stores/bills'

const store = useBillsStore()
const toast = ref({ visible: false, message: '', type: 'info' })
const billsData = ref({ count: 0, oldest: null })
const importing = ref(false)
const fileInput = ref(null)

function showToast(message, type = 'info') {
  toast.value = { visible: true, message, type }
}

function fmtDate(s) {
  if (!s) return ''
  const [y, m, d] = s.slice(0, 10).split('-')
  return `${d}/${m}/${y}`
}

onMounted(async () => {
  await store.fetchBills()
  const all = store.bills
  billsData.value.count = all.length
  if (all.length) {
    billsData.value.oldest = all
      .map((b) => b.createdAt)
      .reduce((min, d) => (d < min ? d : min))
      .slice(0, 10)
  }
})

async function handleImport() {
  const file = fileInput.value?.files?.[0]
  if (!file) return showToast('Seleccioná un archivo', 'warning')
  if (!confirm('¿Reemplazar todos los datos con el archivo importado?\nEsta acción no se puede deshacer.')) return

  importing.value = true
  try {
    const result = await store.importBills(file)
    showToast(`Importación exitosa — ${result.imported} facturas cargadas`, 'success')
    await store.fetchBills()
    billsData.value.count = store.bills.length
    if (fileInput.value) fileInput.value.value = ''
  } catch (e) {
    showToast(e.message || 'Error al importar', 'error')
  } finally {
    importing.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="page-title">Ajustes</h1>

    <section class="card mt-16">
      <h2 class="section-title">Datos</h2>

      <p class="stat-line">{{ billsData.count }} facturas registradas</p>
      <p v-if="billsData.oldest" class="stat-line muted">
        Primera: {{ fmtDate(billsData.oldest) }}
      </p>

      <div class="btn-group mt-16">
        <button class="btn-secondary" @click="store.exportBills()">
          ⬇ Exportar facturas
        </button>

        <label class="btn-secondary file-label">
          ⬆ Importar facturas
          <input
            ref="fileInput"
            type="file"
            accept="application/json,.json"
            class="hidden-input"
            @change="handleImport"
          />
        </label>
      </div>

      <p class="hint mt-12">
        La exportación descarga un <code>bills.json</code> con todas tus facturas.
        La importación reemplaza los datos actuales con un archivo exportado previamente.
      </p>
    </section>

    <ToastNotif v-bind="toast" @close="toast.visible = false" />
  </div>
</template>

<style scoped>
.page-title  { font-size: 1.5rem; font-weight: 700; }
.mt-12 { margin-top: 12px; }
.mt-16 { margin-top: 16px; }

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
}
.section-title {
  font-size: 0.85rem; font-weight: 600; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px;
}
.stat-line { font-size: 0.9rem; margin-bottom: 4px; }
.muted     { color: var(--text-muted); }
.hint      { font-size: 0.8rem; color: var(--text-muted); line-height: 1.5; }
.hint code { background: var(--surface-2); padding: 1px 5px; border-radius: 4px; font-size: 0.85em; }

.btn-group { display: flex; gap: 10px; flex-wrap: wrap; }

.btn-secondary {
  background: var(--surface-2); color: var(--text);
  border: 1px solid var(--border); padding: 10px 16px;
  border-radius: 8px; font-size: 0.875rem; cursor: pointer;
  transition: background 0.15s;
}
.btn-secondary:hover { background: var(--surface-3); }

.file-label {
  display: inline-flex; align-items: center;
  font-family: var(--font);
}
.hidden-input { display: none; }
</style>
