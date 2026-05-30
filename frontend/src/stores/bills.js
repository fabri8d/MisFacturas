/**
 * Pinia store principal de MisFacturas.
 * Centraliza todas las operaciones de facturas y el estado de la UI.
 * Las vistas nunca llaman a api/client.js directamente.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import client from '../api/client'

const currentYearNum = () => new Date().getFullYear()

/** Devuelve YYYY-MM-DD de hoy */
const todayStr = () => new Date().toISOString().slice(0, 10)

/** Devuelve YYYY-MM del mes actual */
const currentMonthStr = () => new Date().toISOString().slice(0, 7)

export const useBillsStore = defineStore('bills', () => {
  // ── State ──────────────────────────────────────────────────────────────────
  const bills = ref([])
  const currentMonth = ref(currentMonthStr())
  const summaryYear = ref(currentYearNum())
  const loading = ref(false)
  const error = ref(null)

  // ── Getters ────────────────────────────────────────────────────────────────

  const billsForMonth = computed(() =>
    bills.value.filter((b) => b.month === currentMonth.value),
  )

  const totalAmount = computed(() =>
    billsForMonth.value.reduce((sum, b) => sum + b.amount, 0),
  )

  const paidAmount = computed(() =>
    billsForMonth.value.filter((b) => b.isPaid).reduce((sum, b) => sum + b.amount, 0),
  )

  const pendingAmount = computed(() => totalAmount.value - paidAmount.value)

  const overdueBills = computed(() => {
    const today = todayStr()
    return billsForMonth.value.filter((b) => !b.isPaid && b.dueDate < today)
  })

  const upcomingBills = computed(() => {
    const today = todayStr()
    const in7 = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10)
    return billsForMonth.value
      .filter((b) => !b.isPaid && b.dueDate >= today && b.dueDate <= in7)
      .sort((a, b) => a.dueDate.localeCompare(b.dueDate))
  })

  // ── Actions ────────────────────────────────────────────────────────────────

  async function fetchBills(month = null) {
    loading.value = true
    error.value = null
    try {
      const params = month ? { month } : {}
      const data = await client.get('/bills', { params })
      bills.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function createBill(payload) {
    loading.value = true
    error.value = null
    try {
      const created = await client.post('/bills', payload)
      await fetchBills()
      return created
    } catch (err) {
      if (err.status === 409) {
        // Duplicado: no es un error crítico, se propaga con flag para mostrar advertencia
        const dupError = new Error('Ya registraste una factura similar — revisá el historial')
        dupError.isDuplicate = true
        dupError.existing = err.message?.existing ?? null
        throw dupError
      }
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateBill(id, payload) {
    loading.value = true
    error.value = null
    try {
      const updated = await client.put(`/bills/${id}`, payload)
      await fetchBills()
      return updated
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteBill(id) {
    loading.value = true
    error.value = null
    try {
      await client.delete(`/bills/${id}`)
      await fetchBills()
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function togglePaid(id) {
    try {
      const updated = await client.patch(`/bills/${id}/toggle-paid`)
      const idx = bills.value.findIndex((b) => b.id === id)
      if (idx !== -1) bills.value[idx] = updated
      return updated
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function scanInvoice(formData) {
    return client.post('/scan-invoice', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  }

  async function fetchSummary(year = null) {
    const params = year ? { year } : { year: summaryYear.value }
    return client.get('/summary', { params })
  }

  function setSummaryYear(year) {
    summaryYear.value = year
  }

  // Estado de integraciones (solo lectura, para chips informativos)
  async function fetchNotificationsConfig() {
    return client.get('/notifications/config')
  }
  async function fetchDriveStatus() {
    return client.get('/drive/status')
  }

  // Exportar JSON
  async function exportBills() {
    const raw = await client.get('/bills')
    const blob = new Blob([JSON.stringify({ bills: raw }, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'bills.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  // Importar JSON
  async function importBills(file) {
    const fd = new FormData()
    fd.append('file', file)
    return client.post('/bills/import', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  }

  return {
    bills,
    currentMonth,
    summaryYear,
    loading,
    error,
    billsForMonth,
    totalAmount,
    paidAmount,
    pendingAmount,
    overdueBills,
    upcomingBills,
    fetchBills,
    createBill,
    updateBill,
    deleteBill,
    togglePaid,
    scanInvoice,
    fetchSummary,
    setSummaryYear,
    fetchNotificationsConfig,
    fetchDriveStatus,
    exportBills,
    importBills,
  }
})
