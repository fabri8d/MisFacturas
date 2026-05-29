/** Router de MisFacturas. Todas las vistas se cargan de forma lazy (code splitting). */
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/DashboardView.vue'),
  },
  {
    path: '/bills',
    name: 'Bills',
    component: () => import('../views/BillsView.vue'),
  },
  {
    path: '/bills/new',
    name: 'NewBill',
    component: () => import('../views/AddEditView.vue'),
  },
  {
    path: '/bills/:id',
    name: 'EditBill',
    component: () => import('../views/AddEditView.vue'),
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('../views/HistoryView.vue'),
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/SettingsView.vue'),
  },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
