<template>
  <v-container class="fill-height" fluid style="overflow-x:hidden">
    <v-row align="center" justify="center" class="fill-height ma-0">
      <v-col cols="12" sm="8" md="5" lg="4" class="px-3">
        <v-card class="pa-6 pa-sm-8 text-center" elevation="2" style="width:100%;max-width:440px;margin:0 auto">
          <v-icon size="72" color="primary" class="mb-4">mdi-receipt-text-outline</v-icon>

          <v-card-title class="text-h4 font-weight-bold pb-1">MisFacturas</v-card-title>
          <v-card-subtitle class="text-body-1 pb-6">
            Gestioná tus facturas fácilmente
          </v-card-subtitle>

          <v-card-text>
            <v-btn
              block
              size="large"
              color="primary"
              :loading="signingIn"
              @click="handleSignIn"
            >
              <template #prepend>
                <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
                  <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
                  <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332C2.438 15.983 5.482 18 9 18z" fill="#34A853"/>
                  <path d="M3.964 10.71c-.18-.54-.282-1.117-.282-1.71s.102-1.17.282-1.71V4.958H.957C.347 6.173 0 7.548 0 9s.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
                  <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
                </svg>
              </template>
              Continuar con Google
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { user, signInWithGoogle } = useAuth()
const signingIn = ref(false)

// Redirigir si ya hay sesión activa
watch(user, (u) => {
  if (u) router.push('/')
}, { immediate: true })

async function handleSignIn() {
  signingIn.value = true
  await signInWithGoogle()
  // El redirect lo maneja Supabase — la página se recarga en /auth/callback
}
</script>
