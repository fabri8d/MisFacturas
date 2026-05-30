import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
  },
  {
    path: '/auth/callback',
    name: 'AuthCallback',
    component: () => import('../views/AuthCallbackView.vue'),
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/DashboardView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/bills',
    name: 'Bills',
    component: () => import('../views/BillsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/bills/new',
    name: 'NewBill',
    component: () => import('../views/AddEditView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/bills/:id',
    name: 'EditBill',
    component: () => import('../views/AddEditView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('../views/HistoryView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/SettingsView.vue'),
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  if (!to.meta.requiresAuth) return true

  const { user, loading } = useAuth()

  // Esperar hasta que se resuelva la sesión inicial
  if (loading.value) {
    await new Promise((resolve) => {
      const stop = setInterval(() => {
        if (!loading.value) {
          clearInterval(stop)
          resolve()
        }
      }, 50)
    })
  }

  if (!user.value) {
    return { name: 'Login' }
  }
  return true
})

export default router
