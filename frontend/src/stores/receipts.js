import { defineStore } from 'pinia'
import { ref } from 'vue'
import client from '../api/client'

export const useReceiptsStore = defineStore('receipts', () => {
  // { bill_id: [ReceiptResponse, ...] }
  const receipts = ref({})
  // { bill_id: number } — para indicadores rápidos sin cargar la lista completa
  const receiptCounts = ref({})
  const uploading = ref(false)
  const error = ref(null)

  // ── Getters ──────────────────────────────────────────────────────────────────

  function hasReceipts(billId) {
    return (receiptCounts.value[billId] || 0) > 0
  }

  function receiptCount(billId) {
    return receiptCounts.value[billId] || 0
  }

  function getReceipts(billId) {
    return receipts.value[billId] || []
  }

  // ── Actions ───────────────────────────────────────────────────────────────────

  async function fetchReceiptCounts() {
    try {
      const data = await client.get('/bills/receipts/summary')
      receiptCounts.value = data || {}
    } catch (e) {
      error.value = e.message
    }
  }

  async function fetchReceipts(billId) {
    try {
      const data = await client.get(`/bills/${billId}/receipts`)
      receipts.value[billId] = data || []
      receiptCounts.value[billId] = (data || []).length
    } catch (e) {
      error.value = e.message
    }
  }

  async function uploadReceipt(billId, file) {
    uploading.value = true
    error.value = null
    try {
      const fd = new FormData()
      fd.append('file', file)
      const receipt = await client.post(`/bills/${billId}/receipts`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      if (!receipts.value[billId]) receipts.value[billId] = []
      receipts.value[billId].unshift(receipt)
      receiptCounts.value[billId] = (receiptCounts.value[billId] || 0) + 1

      // Marcar factura como pagada localmente
      const { useBillsStore } = await import('./bills')
      useBillsStore().markPaid(billId)

      return receipt
    } finally {
      uploading.value = false
    }
  }

  async function deleteReceipt(billId, receiptId) {
    await client.delete(`/bills/${billId}/receipts/${receiptId}`)
    receipts.value[billId] = (receipts.value[billId] || []).filter((r) => r.id !== receiptId)
    receiptCounts.value[billId] = Math.max(0, (receiptCounts.value[billId] || 1) - 1)
  }

  return {
    receipts,
    receiptCounts,
    uploading,
    error,
    hasReceipts,
    receiptCount,
    getReceipts,
    fetchReceiptCounts,
    fetchReceipts,
    uploadReceipt,
    deleteReceipt,
  }
})
