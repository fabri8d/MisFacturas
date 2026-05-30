<template>
  <v-container class="fill-height" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" class="text-center">
        <v-progress-circular indeterminate color="primary" size="48" class="mb-4" />
        <p class="text-body-1 text-medium-emphasis">Iniciando sesión…</p>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { user, loading } = useAuth()

watch([user, loading], ([u, l]) => {
  if (!l && u) {
    router.push('/')
  } else if (!l && !u) {
    router.push('/login')
  }
})
</script>
