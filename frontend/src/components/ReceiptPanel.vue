<template>
  <v-dialog
    :model-value="modelValue"
    :fullscreen="!mdAndUp"
    :max-width="mdAndUp ? 600 : undefined"
    scrollable
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <v-card>
      <!-- Header -->
      <v-toolbar color="surface" border="b" density="compact">
        <v-toolbar-title>
          <span class="text-body-1 font-weight-bold">📎 Comprobantes</span>
          <span v-if="billName" class="text-caption text-medium-emphasis ml-2">{{ billName }}</span>
        </v-toolbar-title>
        <v-btn icon="mdi-close" variant="text" @click="$emit('update:modelValue', false)" />
      </v-toolbar>

      <v-card-text class="pa-4">
        <!-- Sin Drive conectado -->
        <v-alert
          v-if="!hasDrive"
          type="info"
          variant="tonal"
          rounded="lg"
          class="mb-4"
          icon="mdi-google-drive"
        >
          <span class="text-body-2">
            Conectá Google Drive en
            <router-link to="/settings" class="text-primary" @click="$emit('update:modelValue', false)">
              Ajustes
            </router-link>
            para subir comprobantes y que se archiven automáticamente.
          </span>
        </v-alert>

        <!-- Lista de comprobantes -->
        <div v-if="receiptsStore.getReceipts(billId).length === 0 && !receiptsStore.uploading" class="text-center py-6">
          <v-icon size="64" color="grey-lighten-1">mdi-receipt-text-outline</v-icon>
          <p class="text-body-2 text-medium-emphasis mt-2">Sin comprobantes aún</p>
          <p class="text-caption text-medium-emphasis">Subí la foto o PDF del comprobante de pago</p>
        </div>

        <v-list v-else lines="two" class="pa-0 mb-4">
          <v-list-item
            v-for="receipt in receiptsStore.getReceipts(billId)"
            :key="receipt.id"
            rounded="lg"
            border
            class="mb-2"
          >
            <template #prepend>
              <v-icon
                :color="receipt.mimeType === 'application/pdf' ? '#E53935' : '#1E88E5'"
                size="28"
                class="me-2"
              >
                {{ receipt.mimeType === 'application/pdf' ? 'mdi-file-pdf-box' : 'mdi-image' }}
              </v-icon>
            </template>

            <v-list-item-title class="text-body-2">
              {{ truncate(receipt.fileName, 35) }}
            </v-list-item-title>
            <v-list-item-subtitle class="text-caption">
              {{ fmtDate(receipt.uploadedAt) }} · {{ formatSize(receipt.fileSize) }}
            </v-list-item-subtitle>

            <template #append>
              <div class="d-flex">
                <v-btn
                  icon="mdi-open-in-new"
                  variant="text"
                  size="small"
                  title="Ver en Drive"
                  :disabled="!receipt.driveWebViewLink"
                  @click="openInDrive(receipt.driveWebViewLink)"
                />
                <v-btn
                  icon="mdi-download"
                  variant="text"
                  size="small"
                  title="Descargar"
                  :disabled="!receipt.driveWebContentLink"
                  @click="downloadReceipt(receipt)"
                />
                <v-btn
                  icon="mdi-delete"
                  variant="text"
                  size="small"
                  color="error"
                  title="Eliminar"
                  @click="confirmDelete(receipt)"
                />
              </div>
            </template>
          </v-list-item>
        </v-list>

        <!-- Sección de subida (solo con Drive) -->
        <template v-if="hasDrive">
          <v-divider class="mb-4">
            <span class="text-caption text-medium-emphasis px-2">Subir comprobante</span>
          </v-divider>

          <v-file-input
            v-model="selectedFile"
            label="Seleccionar archivo"
            accept="image/jpeg,image/png,image/webp,application/pdf"
            prepend-icon="mdi-upload"
            show-size
            clearable
            :rules="[fileSizeRule]"
            hint="JPG · PNG · WEBP · PDF · máximo 10 MB"
            persistent-hint
            class="mb-3"
            @update:model-value="onFileChange"
          />

          <!-- Preview -->
          <div v-if="selectedFile && previewUrl && isImage" class="mb-3">
            <v-img :src="previewUrl" max-height="150" contain rounded="lg" />
          </div>
          <div v-else-if="selectedFile && !isImage" class="mb-3">
            <v-chip prepend-icon="mdi-file-pdf-box" color="error" variant="tonal" size="small">
              {{ selectedFile.name }}
            </v-chip>
          </div>

          <v-btn
            block
            color="primary"
            :loading="receiptsStore.uploading"
            :disabled="!selectedFile || !!fileError"
            prepend-icon="mdi-cloud-upload"
            @click="handleUpload"
          >
            Subir a Drive
          </v-btn>

          <v-alert
            v-if="uploadSuccess"
            type="success"
            variant="tonal"
            rounded="lg"
            class="mt-3"
            density="compact"
          >
            ✓ Comprobante subido — factura marcada como pagada
          </v-alert>

          <v-alert
            v-if="uploadError"
            type="error"
            variant="tonal"
            rounded="lg"
            class="mt-3"
            density="compact"
          >
            {{ uploadError }}
          </v-alert>
        </template>
      </v-card-text>
    </v-card>
  </v-dialog>

  <!-- Dialog de confirmación de eliminación -->
  <v-dialog v-model="deleteDialog" max-width="380">
    <v-card>
      <v-card-title class="text-body-1 font-weight-bold pt-4 px-4">
        ¿Eliminar este comprobante?
      </v-card-title>
      <v-card-text class="text-body-2 pb-1">
        <strong>{{ pendingDelete?.fileName }}</strong><br>
        <span class="text-medium-emphasis">El archivo también se eliminará de tu Google Drive.</span>
      </v-card-text>
      <v-card-actions class="px-4 pb-3">
        <v-spacer />
        <v-btn variant="text" @click="deleteDialog = false">Cancelar</v-btn>
        <v-btn color="error" :loading="deleting" @click="doDelete">Eliminar</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useDisplay } from 'vuetify'
import { useReceiptsStore } from '../stores/receipts'

const props = defineProps({
  modelValue:   { type: Boolean, required: true },
  billId:       { type: String,  default: null },
  billName:     { type: String,  default: '' },
  billDueDate:  { type: String,  default: null },
  hasDrive:     { type: Boolean, default: false },
})
defineEmits(['update:modelValue'])

const { mdAndUp } = useDisplay()
const receiptsStore = useReceiptsStore()

const selectedFile = ref(null)
const previewUrl = ref(null)
const fileError = ref('')
const uploadSuccess = ref(false)
const uploadError = ref('')
const deleteDialog = ref(false)
const pendingDelete = ref(null)
const deleting = ref(false)

const isImage = computed(() =>
  selectedFile.value?.type?.startsWith('image/') ?? false
)

function fileSizeRule(file) {
  if (!file) return true
  return file.size < 10 * 1024 * 1024 || 'Máximo 10 MB'
}

function onFileChange(file) {
  uploadSuccess.value = false
  uploadError.value = ''
  if (previewUrl.value) { URL.revokeObjectURL(previewUrl.value); previewUrl.value = null }
  if (!file) { fileError.value = ''; return }

  const rule = fileSizeRule(file)
  fileError.value = rule === true ? '' : rule

  if (rule === true && file.type.startsWith('image/')) {
    previewUrl.value = URL.createObjectURL(file)
  }
}

async function handleUpload() {
  if (!selectedFile.value || fileError.value) return
  uploadSuccess.value = false
  uploadError.value = ''
  try {
    await receiptsStore.uploadReceipt(props.billId, selectedFile.value)
    uploadSuccess.value = true
    selectedFile.value = null
    if (previewUrl.value) { URL.revokeObjectURL(previewUrl.value); previewUrl.value = null }
  } catch (e) {
    uploadError.value = e.message?.message || e.message || 'Error al subir el comprobante'
  }
}

function openInDrive(url) {
  if (url) window.open(url, '_blank')
}

function downloadReceipt(receipt) {
  if (receipt.driveWebContentLink) window.open(receipt.driveWebContentLink, '_blank')
}

function confirmDelete(receipt) {
  pendingDelete.value = receipt
  deleteDialog.value = true
}

async function doDelete() {
  if (!pendingDelete.value) return
  deleting.value = true
  try {
    await receiptsStore.deleteReceipt(props.billId, pendingDelete.value.id)
    deleteDialog.value = false
    pendingDelete.value = null
  } finally {
    deleting.value = false
  }
}

function truncate(str, max) {
  if (!str || str.length <= max) return str
  return str.slice(0, max) + '…'
}

function fmtDate(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch { return iso }
}

function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1048576) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

// Cargar receipts cuando se abre el panel o cambia el billId
watch(() => [props.modelValue, props.billId], ([open, id]) => {
  if (open && id) {
    uploadSuccess.value = false
    uploadError.value = ''
    receiptsStore.fetchReceipts(id)
  }
})

onBeforeUnmount(() => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})
</script>
