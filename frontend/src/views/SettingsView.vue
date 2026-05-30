<template>
  <div>
    <h1 class="text-h5 font-weight-bold mb-4">Ajustes</h1>

    <!-- Mi cuenta -->
    <v-card border elevation="0" rounded="lg" class="mb-4">
      <v-card-title class="text-caption text-uppercase text-medium-emphasis pt-3 px-4 pb-0">
        Mi cuenta
      </v-card-title>
      <v-list-item class="py-3 px-4">
        <template #prepend>
          <v-avatar :image="user?.user_metadata?.avatar_url" size="48" color="primary" class="me-3">
            <v-icon v-if="!user?.user_metadata?.avatar_url">mdi-account</v-icon>
          </v-avatar>
        </template>
        <v-list-item-title class="font-weight-medium">
          {{ user?.user_metadata?.full_name || user?.email }}
        </v-list-item-title>
        <v-list-item-subtitle>{{ user?.email }}</v-list-item-subtitle>
      </v-list-item>
      <v-card-actions class="px-4 pb-3">
        <v-btn
          variant="outlined"
          color="error"
          prepend-icon="mdi-logout"
          size="small"
          @click="handleSignOut"
        >
          Cerrar sesión
        </v-btn>
      </v-card-actions>
    </v-card>

    <!-- Datos -->
    <v-card border elevation="0" rounded="lg" class="mb-4 pa-4">
      <div class="text-caption text-uppercase text-medium-emphasis font-weight-semibold mb-3">
        Datos
      </div>
      <p class="text-body-2 mb-1">{{ billsData.count }} facturas registradas</p>
      <p v-if="billsData.oldest" class="text-body-2 text-medium-emphasis mb-3">
        Primera: {{ fmtDate(billsData.oldest) }}
      </p>
      <div class="d-flex gap-2 flex-wrap">
        <v-btn
          variant="outlined"
          size="small"
          prepend-icon="mdi-download"
          @click="store.exportBills()"
        >
          Exportar
        </v-btn>
        <v-btn
          variant="outlined"
          size="small"
          prepend-icon="mdi-upload"
          @click="triggerImport"
        >
          Importar
        </v-btn>
        <input
          ref="fileInput"
          type="file"
          accept="application/json,.json"
          class="d-none"
          @change="handleImport"
        />
      </div>
      <p class="text-caption text-medium-emphasis mt-3">
        La exportación descarga un <code>bills.json</code>. La importación reemplaza los datos actuales.
      </p>
    </v-card>

    <!-- Notificaciones Telegram -->
    <v-card border elevation="0" rounded="lg" class="mb-4 pa-4">
      <div class="text-caption text-uppercase text-medium-emphasis font-weight-semibold mb-3">
        Notificaciones Telegram
      </div>

      <v-text-field
        v-model="telegramChatId"
        label="Tu Chat ID de Telegram"
        placeholder="Ej: 123456789"
        hint="Buscá @userinfobot en Telegram para obtener tu ID"
        persistent-hint
        class="mb-2"
      />
      <v-switch
        v-model="notificationsEnabled"
        color="primary"
        label="Recibir notificaciones diarias"
        hide-details
        class="mb-3"
      />
      <div class="d-flex gap-2 flex-wrap">
        <v-btn
          color="primary"
          size="small"
          :loading="savingNotif"
          @click="saveNotifConfig"
        >
          Guardar
        </v-btn>
        <v-btn
          variant="outlined"
          size="small"
          prepend-icon="mdi-send"
          :loading="testingTelegram"
          @click="testTelegram"
        >
          Probar
        </v-btn>
      </div>

      <v-expansion-panels class="mt-3" variant="accordion">
        <v-expansion-panel title="¿Cómo obtener mi Chat ID?">
          <v-expansion-panel-text class="text-body-2 text-medium-emphasis">
            1. Abrí Telegram y buscá <strong>@userinfobot</strong><br>
            2. Enviá <code>/start</code><br>
            3. Copiá el número "Id:" que te responde<br>
            4. Pegalo en el campo de arriba y guardá
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card>

    <!-- Google Drive -->
    <v-card border elevation="0" rounded="lg" class="pa-4">
      <div class="text-caption text-uppercase text-medium-emphasis font-weight-semibold mb-3">
        Google Drive
      </div>

      <!-- Estado A: no conectado -->
      <template v-if="!driveStatus.connected">
        <p class="text-body-2 text-medium-emphasis mb-3">
          Conectá tu Google Drive para detectar facturas automáticamente.
        </p>
        <v-btn color="primary" prepend-icon="mdi-google-drive" @click="connectDrive">
          Conectar Google Drive
        </v-btn>
      </template>

      <!-- Estado B: conectado sin carpeta -->
      <template v-else-if="driveStatus.connected && !driveStatus.folder_id">
        <v-chip color="success" variant="tonal" size="small" class="mb-3">
          <v-icon start>mdi-check-circle</v-icon>
          {{ driveStatus.account_email }}
        </v-chip>
        <v-text-field
          v-model="folderId"
          label="ID de carpeta de Drive"
          placeholder="Pegá el ID de la carpeta"
          hint="Visible en la URL de la carpeta al abrirla en el browser"
          persistent-hint
          class="mb-2"
        />
        <v-btn color="primary" size="small" :loading="savingFolder" @click="saveFolder">
          Guardar carpeta
        </v-btn>
      </template>

      <!-- Estado C: conectado con carpeta -->
      <template v-else>
        <v-chip color="success" variant="tonal" size="small" class="mb-2">
          <v-icon start>mdi-check-circle</v-icon>
          Conectado: {{ driveStatus.account_email }}
        </v-chip>
        <p class="text-body-2 text-medium-emphasis mb-3">
          <v-icon size="16" class="me-1">mdi-folder-outline</v-icon>
          {{ driveStatus.folder_name || driveStatus.folder_id }}
        </p>
        <v-btn
          variant="outlined"
          color="error"
          size="small"
          prepend-icon="mdi-link-off"
          :loading="disconnecting"
          @click="disconnectDrive"
        >
          Desconectar
        </v-btn>
      </template>
    </v-card>

    <ToastNotif v-bind="toast" @close="toast.visible = false" />

    <!-- Confirm import dialog -->
    <v-dialog v-model="confirmImport" max-width="420">
      <v-card>
        <v-card-title>¿Importar facturas?</v-card-title>
        <v-card-text class="text-body-2">
          Esta acción reemplazará <strong>todas</strong> tus facturas actuales. No se puede deshacer.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="confirmImport = false">Cancelar</v-btn>
          <v-btn color="error" :loading="importing" @click="doImport">Importar</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import ToastNotif from '../components/ToastNotif.vue'
import { useAuth } from '../composables/useAuth'
import client from '../api/client'
import { useBillsStore } from '../stores/bills'

const store = useBillsStore()
const router = useRouter()
const { user, signOut } = useAuth()

const toast = ref({ visible: false, message: '', type: 'info' })
const billsData = ref({ count: 0, oldest: null })
const fileInput = ref(null)
const pendingFile = ref(null)
const importing = ref(false)
const confirmImport = ref(false)

const telegramChatId = ref('')
const notificationsEnabled = ref(true)
const savingNotif = ref(false)
const testingTelegram = ref(false)

const driveStatus = ref({ connected: false, folder_id: null, folder_name: null, account_email: null })
const folderId = ref('')
const savingFolder = ref(false)
const disconnecting = ref(false)

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

  try {
    const notif = await store.fetchNotificationsConfig()
    notificationsEnabled.value = notif.enabled
    telegramChatId.value = notif.telegram_chat_id || ''
  } catch { /* opcional */ }

  try {
    const drive = await store.fetchDriveStatus()
    driveStatus.value = drive
  } catch { /* opcional */ }
})

function triggerImport() {
  fileInput.value?.click()
}

function handleImport(e) {
  const file = e.target.files?.[0]
  if (!file) return
  pendingFile.value = file
  confirmImport.value = true
}

async function doImport() {
  if (!pendingFile.value) return
  importing.value = true
  try {
    const result = await store.importBills(pendingFile.value)
    showToast(`Importación exitosa — ${result.imported} facturas cargadas`, 'success')
    await store.fetchBills()
    billsData.value.count = store.bills.length
    if (fileInput.value) fileInput.value.value = ''
    pendingFile.value = null
  } catch (e) {
    showToast(e.message || 'Error al importar', 'error')
  } finally {
    importing.value = false
    confirmImport.value = false
  }
}

async function saveNotifConfig() {
  savingNotif.value = true
  try {
    await client.patch('/notifications/config', {
      notifications_enabled: notificationsEnabled.value,
      telegram_chat_id: telegramChatId.value || null,
    })
    showToast('Configuración guardada', 'success')
  } catch (e) {
    showToast(e.message, 'error')
  } finally {
    savingNotif.value = false
  }
}

async function testTelegram() {
  testingTelegram.value = true
  try {
    const res = await client.post('/notifications/test', {})
    showToast(res.message, res.ok ? 'success' : 'error')
  } catch (e) {
    showToast(e.message, 'error')
  } finally {
    testingTelegram.value = false
  }
}

async function connectDrive() {
  try {
    const res = await client.get('/drive/oauth/start')
    window.location.href = res.auth_url
  } catch (e) {
    showToast(e.message, 'error')
  }
}

async function saveFolder() {
  savingFolder.value = true
  try {
    await client.post('/drive/set-folder', { folder_id: folderId.value })
    const drive = await store.fetchDriveStatus()
    driveStatus.value = drive
    showToast('Carpeta configurada', 'success')
  } catch (e) {
    showToast(e.message, 'error')
  } finally {
    savingFolder.value = false
  }
}

async function disconnectDrive() {
  disconnecting.value = true
  try {
    await client.post('/drive/disconnect', {})
    driveStatus.value = { connected: false, folder_id: null, folder_name: null, account_email: null }
    showToast('Drive desconectado', 'success')
  } catch (e) {
    showToast(e.message, 'error')
  } finally {
    disconnecting.value = false
  }
}

async function handleSignOut() {
  await signOut()
  router.push('/login')
}
</script>
