<script setup>
/**
 * Vista de alta/edición de factura.
 * En modo "nueva" muestra la sección de escaneo con IA.
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CategoryPicker from '../components/CategoryPicker.vue'
import ToastNotif from '../components/ToastNotif.vue'
import { useBillsStore } from '../stores/bills'

const store = useBillsStore()
const route = useRoute()
const router = useRouter()

const isNew = computed(() => route.name === 'NewBill')
const billId = computed(() => route.params.id)

const form = ref({
  name: '',
  category: 'otro',
  amount: '',
  dueDate: '',
  notes: '',
  isPaid: false,
  paidDate: null,
  source: 'manual',
})

const scanning = ref(false)
const saving = ref(false)
const toast = ref({ visible: false, message: '', type: 'info' })
const fileInput = ref(null)

function showToast(message, type = 'error') {
  toast.value = { visible: true, message, type }
}

onMounted(async () => {
  if (!isNew.value) {
    await store.fetchBills()
    const bill = store.bills.find((b) => b.id === billId.value)
    if (bill) Object.assign(form.value, { ...bill, amount: String(bill.amount) })
  }
})

async function handleScan() {
  const file = fileInput.value?.files?.[0]
  if (!file) return showToast('Seleccioná un archivo primero')

  scanning.value = true
  try {
    const fd = new FormData()
    fd.append('invoice', file)
    const result = await store.scanInvoice(fd)

    if (result.name)     form.value.name = result.name
    if (result.category) form.value.category = result.category
    if (result.amount != null) form.value.amount = String(result.amount)
    if (result.dueDate)  form.value.dueDate = result.dueDate
    if (result.notes)    form.value.notes = result.notes

    showToast('Factura escaneada correctamente', 'success')
  } catch (e) {
    showToast('Error al escanear: ' + e.message)
  } finally {
    scanning.value = false
  }
}

async function handleSubmit() {
  if (!form.value.name.trim()) return showToast('El nombre es requerido')
  const amt = parseFloat(form.value.amount)
  if (!form.value.amount || isNaN(amt) || amt <= 0) return showToast('El monto debe ser mayor a 0')
  if (!form.value.dueDate) return showToast('La fecha de vencimiento es requerida')

  saving.value = true
  try {
    const payload = {
      ...form.value,
      amount: amt,
      paidDate: form.value.isPaid
        ? (form.value.paidDate || new Date().toISOString().slice(0, 10))
        : null,
    }
    if (isNew.value) {
      await store.createBill(payload)
      showToast('Factura creada correctamente', 'success')
    } else {
      await store.updateBill(billId.value, payload)
      showToast('Factura actualizada correctamente', 'success')
    }
    setTimeout(() => router.push('/bills'), 1000)
  } catch (e) {
    if (e.isDuplicate) {
      showToast(e.message, 'warning')
      setTimeout(() => router.push('/bills'), 2000)
      return
    }
    showToast(e.message)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <div class="header">
      <button class="back-btn" @click="router.back()">← Volver</button>
      <h1 class="page-title">{{ isNew ? 'Nueva factura' : 'Editar factura' }}</h1>
    </div>

    <!-- Sección de escaneo con IA (solo en modo nueva) -->
    <section v-if="isNew" class="scan-section">
      <h2 class="section-title">Escanear con IA</h2>
      <p class="hint">Subí una imagen o PDF de la factura para completar el formulario automáticamente.</p>
      <div class="scan-row">
        <input
          ref="fileInput"
          type="file"
          accept="image/*,.pdf"
          class="file-input"
        />
        <button class="scan-btn" :disabled="scanning" @click="handleScan">
          {{ scanning ? 'Escaneando...' : '🔍 Escanear con IA' }}
        </button>
      </div>
    </section>

    <!-- Formulario -->
    <form class="form mt-24" @submit.prevent="handleSubmit">
      <div class="field">
        <label>Categoría</label>
        <CategoryPicker v-model="form.category" />
      </div>

      <div class="field">
        <label for="name">Nombre <span class="required">*</span></label>
        <input id="name" v-model="form.name" type="text" placeholder="Ej: Edesur, Metrogas..." required />
      </div>

      <div class="field">
        <label for="amount">Monto (ARS) <span class="required">*</span></label>
        <input id="amount" v-model="form.amount" type="number" min="0.01" step="0.01" placeholder="0.00" required />
      </div>

      <div class="field">
        <label for="dueDate">Fecha de vencimiento <span class="required">*</span></label>
        <input id="dueDate" v-model="form.dueDate" type="date" required />
      </div>

      <div class="field">
        <label for="notes">Notas (opcional)</label>
        <textarea id="notes" v-model="form.notes" rows="2" placeholder="Información adicional..." />
      </div>

      <label class="checkbox-row">
        <input v-model="form.isPaid" type="checkbox" />
        <span>Ya está pagada</span>
      </label>

      <div class="btn-row">
        <button type="button" class="btn-cancel" @click="router.back()">Cancelar</button>
        <button type="submit" class="btn-save" :disabled="saving">
          {{ saving ? 'Guardando...' : 'Guardar' }}
        </button>
      </div>
    </form>

    <ToastNotif v-bind="toast" @close="toast.visible = false" />
  </div>
</template>

<style scoped>
.header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.back-btn { background: transparent; color: var(--text-muted); font-size: 0.9rem; padding: 4px 0; }
.page-title { font-size: 1.25rem; font-weight: 700; }
.mt-24 { margin-top: 24px; }
.section-title { font-size: 0.85rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
.hint { font-size: 0.82rem; color: var(--text-muted); margin-bottom: 12px; }

.scan-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
}
.scan-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.file-input { flex: 1; font-size: 0.85rem; color: var(--text); background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; padding: 8px; }
.scan-btn {
  background: var(--accent); color: #000; font-weight: 600;
  padding: 10px 16px; border-radius: 8px; font-size: 0.875rem; white-space: nowrap;
}
.scan-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.form { display: flex; flex-direction: column; gap: 16px; }
.field { display: flex; flex-direction: column; gap: 6px; }
label { font-size: 0.82rem; font-weight: 500; color: var(--text-muted); }
.required { color: var(--danger); }
input[type="text"], input[type="number"], input[type="date"], textarea {
  background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px;
  color: var(--text); padding: 10px 12px; font-size: 0.9rem;
  transition: border-color 0.15s;
}
input:focus, textarea:focus { outline: none; border-color: var(--accent); }
textarea { resize: vertical; }

.checkbox-row { display: flex; align-items: center; gap: 10px; font-size: 0.9rem; cursor: pointer; }
.checkbox-row input { width: 16px; height: 16px; accent-color: var(--accent); }

.btn-row { display: flex; gap: 10px; justify-content: flex-end; margin-top: 8px; }
.btn-cancel { background: var(--surface-2); color: var(--text-muted); border: 1px solid var(--border); padding: 10px 18px; border-radius: 8px; font-size: 0.875rem; }
.btn-save { background: var(--accent); color: #000; font-weight: 600; padding: 10px 20px; border-radius: 8px; font-size: 0.875rem; }
.btn-save:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
