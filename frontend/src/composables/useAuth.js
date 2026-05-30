import { computed, ref, watch } from 'vue'
import { supabase } from '../plugins/supabase'

const user = ref(null)
const loading = ref(true)

supabase.auth.getSession().then(({ data: { session } }) => {
  user.value = session?.user ?? null
  loading.value = false
})

supabase.auth.onAuthStateChange((_event, session) => {
  user.value = session?.user ?? null
  loading.value = false
})

// Computed properties based on user metadata
const avatarUrl = computed(() => user.value?.user_metadata?.avatar_url || null)

const fullName = computed(() =>
  user.value?.user_metadata?.full_name || user.value?.email || ''
)

const userInitials = computed(() => {
  const name = fullName.value
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
})

export function useAuth() {
  async function signInWithGoogle() {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    })
  }

  async function signOut() {
    await supabase.auth.signOut()
  }

  async function getAccessToken() {
    const { data: { session } } = await supabase.auth.getSession()
    return session?.access_token ?? null
  }

  return { user, loading, avatarUrl, fullName, userInitials, signInWithGoogle, signOut, getAccessToken }
}
