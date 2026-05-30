<template>
  <v-app>
    <template v-if="user && !isAuthRoute">

      <!-- ── App Bar ──────────────────────────────────────────────────────── -->
      <v-app-bar flat border="b" color="surface" :elevation="0">
        <v-btn
          v-if="mdAndUp"
          :icon="rail ? 'mdi-menu' : 'mdi-menu-open'"
          variant="text"
          @click="rail = !rail"
        />
        <v-app-bar-title>
          <span class="font-weight-bold text-primary" style="font-family: var(--font-display)">
            MisFacturas
          </span>
        </v-app-bar-title>
        <template #append>
          <v-chip v-if="driveOk" size="x-small" color="success" variant="tonal" class="me-1">
            <v-icon start size="12">mdi-google-drive</v-icon>Drive
          </v-chip>
          <v-chip v-if="telegramOk" size="x-small" color="success" variant="tonal" class="me-2">
            <v-icon start size="12">mdi-send</v-icon>Telegram
          </v-chip>
          <v-avatar
            size="34"
            color="primary"
            class="me-2"
            style="cursor:pointer"
            @click="router.push('/settings')"
          >
            <v-img
              v-if="avatarUrl && !imgError"
              :src="avatarUrl"
              :alt="fullName"
              @error="imgError = true"
            />
            <span v-else style="font-size:13px;font-weight:700;color:white">
              {{ userInitials }}
            </span>
          </v-avatar>
        </template>
      </v-app-bar>

      <!-- ── Desktop Navigation Drawer ──────────────────────────────────── -->
      <v-navigation-drawer
        v-if="mdAndUp"
        :rail="rail"
        permanent
        color="surface"
        border="e"
        rail-width="68"
      >
        <v-list nav density="compact" class="mt-2">
          <v-list-item
            v-for="item in navItems"
            :key="item.to"
            :prepend-icon="item.icon"
            :title="item.label"
            :to="item.to"
            :exact="item.to === '/'"
            rounded="lg"
            active-color="primary"
          />
        </v-list>

        <template #append>
          <v-divider />
          <v-list nav density="compact" class="py-2">
            <v-list-item :prepend-avatar="avatarUrl || undefined" :title="rail ? undefined : (fullName || user?.email)">
              <template v-if="!rail" #append>
                <v-tooltip text="Cerrar sesión" location="top">
                  <template #activator="{ props }">
                    <v-btn
                      v-bind="props"
                      icon="mdi-logout"
                      variant="text"
                      size="small"
                      color="error"
                      @click="handleSignOut"
                    />
                  </template>
                </v-tooltip>
              </template>
            </v-list-item>
          </v-list>
        </template>
      </v-navigation-drawer>

      <!-- ── Main Content ────────────────────────────────────────────────── -->
      <v-main>
        <v-container
          :max-width="mdAndUp ? 960 : 680"
          :class="['pt-4', 'px-3', { 'pb-20': !mdAndUp }]"
        >
          <router-view />
        </v-container>
      </v-main>

      <!-- ── Mobile Bottom Navigation ───────────────────────────────────── -->
      <v-bottom-navigation
        v-if="!mdAndUp"
        grow
        color="primary"
        :elevation="0"
        border="t"
        bg-color="surface"
      >
        <v-btn v-for="item in navItems" :key="item.to" :to="item.to">
          <v-icon>{{ item.icon }}</v-icon>
          <span>{{ item.label }}</span>
        </v-btn>
      </v-bottom-navigation>
    </template>

    <!-- Auth routes (login/callback) -->
    <template v-else>
      <v-main>
        <router-view />
      </v-main>
    </template>
  </v-app>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import { useAuth } from './composables/useAuth'
import { useBillsStore } from './stores/bills'

const route = useRoute()
const router = useRouter()
const { user, avatarUrl, fullName, userInitials, signOut } = useAuth()
const store = useBillsStore()
const { mdAndUp } = useDisplay()

const rail = ref(true)
const driveOk = ref(false)
const telegramOk = ref(false)
const imgError = ref(false)

// Reset image error when avatar URL changes (new login)
watch(avatarUrl, () => { imgError.value = false })

const isAuthRoute = computed(() =>
  route.name === 'Login' || route.name === 'AuthCallback'
)

const navItems = [
  { to: '/',         icon: 'mdi-home-outline',           label: 'Inicio' },
  { to: '/bills',    icon: 'mdi-receipt-text-outline',   label: 'Facturas' },
  { to: '/history',  icon: 'mdi-chart-bar',              label: 'Historial' },
  { to: '/settings', icon: 'mdi-cog-outline',            label: 'Ajustes' },
]

async function handleSignOut() {
  await signOut()
  router.push('/login')
}

onMounted(async () => {
  if (!user.value) return
  try {
    const [drive, notif] = await Promise.all([
      store.fetchDriveStatus(),
      store.fetchNotificationsConfig(),
    ])
    driveOk.value = drive.connected && !!drive.folder_id
    telegramOk.value = notif.telegram_configured
  } catch { /* chips opcionales */ }
})
</script>
