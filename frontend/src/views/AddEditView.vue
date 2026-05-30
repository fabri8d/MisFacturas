<template>
  <div>
    <div class="d-flex align-center gap-3 mb-4">
      <v-btn
        icon="mdi-arrow-left"
        variant="text"
        size="small"
        @click="router.back()"
      />
      <h1 class="text-h6 font-weight-bold">
        {{ isNew ? 'Nueva factura' : 'Editar factura' }}
      </h1>
    </div>

    <!-- Sección AI scan (solo modo nueva) -->
    <v-card v-if="isNew" border elevation="0" rounded="lg" class="mb-4 pa-4">
      <div class="text-caption text-uppercase text-medium-emphasis font-weight-semibold mb-2">
        Escanear con IA
      </div>
      <p class="text-body-2 text-medium-emphasis mb-3">
        Subí una imagen o PDF para completar el formulario automáticamente.
      </p>

      <v-file-input
        v-model="scanFile"
        label="Factura (imagen o PDF)"
        accept="image/*,.pdf"
        prepend-icon=""
        prepend-inner-icon="mdi-file-upload-outline"
        hide-details
        density="comfortable"
        class="mb-3"
        clearable
      />

      <div class="d-flex align-center gap-2 flex-wrap">
        <v-btn
          color="primary"
          :loading="scanning"
          :disabled="!scanFile"
          prepend-icon="mdi-magnify"
          @click="handleScan"
        >
          Escanear con IA
        </v-btn>

        <v-chip
          v-if="driveConnected"
          size="small"
          color="success"
          variant="tonal"
          prepend-icon="mdi-google-drive"
        >
          Se archivará en Drive
        </v-chip>
        <span v-else class="text-caption text-medium-emphasis">Solo escaneo local</span>
      </div>
    </v-card>

    <!-- Formulario -->
    <v-form ref="formRef" @submit.prevent="handleSubmit">
      <!-- Categoría -->
      <div class="text-caption text-medium-emphasis font-weight-semibold mb-2">Categoría</div>
      <CategoryPicker v-model="form.category" class="mb-4" />

      <v-text-field
        v-model="form.name"
        label="Nombre *"
        placeholder="Ej: Edesur, Metrogas..."
        :rules="[v => !!v?.trim() || 'El nombre es requerido']"
        class="mb-2"
      />

      <v-text-field
        v-model="form.amount"
        label="Monto (ARS) *"
        type="number"
        min="0.01"
        step="0.01"
        placeholder="0.00"
        :rules="[v => (parseFloat(v) > 0) || 'El monto debe ser mayor a 0']"
        class="mb-2"
      />

      <v-text-field
        v-model="displayDate"
        label="Fecha de vencimiento *"
        placeholder="DD/MM/AAAA"
        :rules="[v => /^\d{2}\/\d{2}\/\d{4}$/.test(v) || 'Ingresá la fecha como DD/MM/AAAA']"
        :error-messages="dateError"
        class="mb-2"
        @input="parseDate"
      />

      <v-textarea
        v-model="form.notes"
        label="Notas (opcional)"
        placeholder="Información adicional..."
        rows="2"
        auto-grow
        class="mb-2"
      />

      <v-checkbox
        v-model="form.isPaid"
        label="Ya está pagada"
        color="success"
        hide-details
        class="mb-4"
      />

      <div class="d-flex justify-end gap-2">
        <v-btn variant="text" @click="router.back()">Cancelar</v-btn>
        <v-btn
          type="submit"
          color="primary"
          :loading="saving"
        >
          Guardar
        </v-btn>
      </div>
    </v-form>

    <!-- Overlay scan -->
    <v-overlay v-model="scanning" class="align-center justify-center" persistent>
      <v-progress-circular indeterminate color="primary" size="48" />
    </v-overlay>

    <ToastNotif v-bind="toast" @close="toast.visible = false" />
  </div>
</template>

<script setup>
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

const displayDate = ref('')
const dateError = ref('')
const scanning = ref(false)
const saving = ref(false)
const scanFile = ref(null)
const formRef = ref(null)
const driveConnected = ref(false)
const toast = ref({ visible: false, message: '', type: 'info' })

function showToast(message, type = 'error') {
  toast.value = { visible: true, message, type }
}

function parseDate(val) {
  const raw = typeof val === 'string' ? val : val?.target?.value ?? ''
  const match = raw.match(/^(\d{2})\/(\d{2})\/(\d{4})$/)
  if (match) {
    form.value.dueDate = `${match[3]}-${match[2]}-${match[1]}`
    dateError.value = ''
  } else if (raw.length === 10) {
    form.value.dueDate = ''
    dateError.value = 'Ingresá la fecha como DD/MM/AAAA'
  }
}

function toDisplay(iso) {
  if (!iso) return ''
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

onMounted(async () => {
  if (!isNew.value) {
    await store.fetchBills()
    const bill = store.bills.find((b) => b.id === billId.value)
    if (bill) {
      Object.assign(form.value, { ...bill, amount: String(bill.amount) })
      displayDate.value = toDisplay(bill.dueDate)
    }
  }
  try {
    const drive = await store.fetchDriveStatus()
    driveConnected.value = drive.connected && !!drive.folder_id
  } catch { /* opcional */ }
})

async function handleScan() {
  if (!scanFile.value) return showToast('Seleccioná un archivo primero')
  scanning.value = true
  try {
    const fd = new FormData()
    fd.append('invoice', scanFile.value)
    const result = await store.scanInvoice(fd)

    if (result.name)          form.value.name = result.name
    if (result.category)      form.value.category = result.category
    if (result.amount != null) form.value.amount = String(result.amount)
    if (result.dueDate) {
      form.value.dueDate = result.dueDate
      displayDate.value = toDisplay(result.dueDate)
    }
    if (result.notes) form.value.notes = result.notes

    showToast('Factura escaneada correctamente', 'success')
  } catch (e) {
    showToast('Error al escanear: ' + e.message)
  } finally {
    scanning.value = false
  }
}

async function handleSubmit() {
  const { valid } = await formRef.value.validate()
  if (!valid || !form.value.dueDate) {
    if (!form.value.dueDate) dateError.value = 'Ingresá la fecha como DD/MM/AAAA'
    return
  }

  saving.value = true
  try {
    const payload = {
      ...form.value,
      amount: parseFloat(form.value.amount),
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
