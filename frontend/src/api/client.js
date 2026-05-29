/**
 * Cliente HTTP de MisFacturas.
 * Instancia de Axios con baseURL desde la variable de entorno VITE_API_BASE_URL.
 * El interceptor de respuesta desenvuelve data y normaliza los errores.
 */
import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
})

client.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const detail = error.response?.data?.detail
    // detail puede ser string o un objeto {message, existing} (ej. 409 duplicado)
    const message = typeof detail === 'object' ? detail : (detail || error.message || 'Error desconocido')
    const status = error.response?.status ?? 0
    return Promise.reject({ message, status })
  },
)

export default client
