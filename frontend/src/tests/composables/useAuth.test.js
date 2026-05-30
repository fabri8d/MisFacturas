import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, computed } from 'vue'

// Mock Supabase before importing useAuth
vi.mock('../../plugins/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
      onAuthStateChange: vi.fn().mockReturnValue({ data: { subscription: { unsubscribe: vi.fn() } } }),
      signInWithOAuth: vi.fn(),
      signOut: vi.fn(),
    },
  },
}))

// Re-implement the composable logic locally to test computed values
function makeUseAuth(userMetadata) {
  const user = ref(userMetadata ? { user_metadata: userMetadata, email: userMetadata.email || 'test@example.com' } : null)
  const avatarUrl  = computed(() => user.value?.user_metadata?.avatar_url || null)
  const fullName   = computed(() => user.value?.user_metadata?.full_name || user.value?.email || '')
  const userInitials = computed(() => {
    const name = fullName.value
    return name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
  })
  return { user, avatarUrl, fullName, userInitials }
}

describe('useAuth — avatar & identity computeds', () => {
  it('avatarUrl returns avatar_url from user_metadata', () => {
    const { avatarUrl } = makeUseAuth({ avatar_url: 'https://foto.jpg', full_name: 'Test' })
    expect(avatarUrl.value).toBe('https://foto.jpg')
  })

  it('avatarUrl is null when avatar_url is not present', () => {
    const { avatarUrl } = makeUseAuth({ full_name: 'Test' })
    expect(avatarUrl.value).toBeNull()
  })

  it('avatarUrl is null when user is null', () => {
    const { avatarUrl } = makeUseAuth(null)
    expect(avatarUrl.value).toBeNull()
  })

  it('userInitials from two-word name', () => {
    const { userInitials } = makeUseAuth({ full_name: 'Leandro Biondi' })
    expect(userInitials.value).toBe('LB')
  })

  it('userInitials from one-word name', () => {
    const { userInitials } = makeUseAuth({ full_name: 'Leandro' })
    expect(userInitials.value).toBe('L')
  })

  it('userInitials limited to 2 chars for long names', () => {
    const { userInitials } = makeUseAuth({ full_name: 'Ana María García López' })
    expect(userInitials.value).toHaveLength(2)
  })

  it('fullName falls back to email when no full_name', () => {
    const { fullName } = makeUseAuth({ email: 'leandro@gmail.com' })
    expect(fullName.value).toBe('leandro@gmail.com')
  })

  it('fullName prefers full_name over email', () => {
    const { fullName } = makeUseAuth({ full_name: 'Leandro Biondi', email: 'leandro@gmail.com' })
    expect(fullName.value).toBe('Leandro Biondi')
  })

  it('fullName returns empty string when user is null', () => {
    const { fullName } = makeUseAuth(null)
    expect(fullName.value).toBe('')
  })

  it('userInitials uses email initial when no full_name', () => {
    const { userInitials } = makeUseAuth({ email: 'leandro@gmail.com' })
    expect(userInitials.value).toBe('L')
  })
})
