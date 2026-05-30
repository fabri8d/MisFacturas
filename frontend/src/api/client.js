/**
 * Cliente HTTP de MisFacturas v2.
 * Agrega el JWT de Supabase en cada request.
 * Si el servidor responde 401, cierra la sesión y redirige al login.
 */
import axios from 'axios'
import { useAuth } from '../composables/useAuth'
import router from '../router/index'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
})

client.interceptors.request.use(async (config) => {
  const { getAccessToken } = useAuth()
  const token = await getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    if (error.response?.status === 401) {
      const { signOut } = useAuth()
      await signOut()
      router.push('/login')
    }
    const detail = error.response?.data?.detail
    const message = typeof detail === 'object' ? detail : (detail || error.message || 'Error desconocido')
    const status = error.response?.status ?? 0
    return Promise.reject({ message, status })
  },
)

export default client
