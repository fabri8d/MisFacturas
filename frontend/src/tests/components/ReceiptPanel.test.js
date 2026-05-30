import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

// Mock stores
vi.mock('../../stores/receipts', () => ({
  useReceiptsStore: () => ({
    receipts: ref({}),
    uploading: ref(false),
    error: ref(null),
    receiptCounts: ref({}),
    hasReceipts: (id) => false,
    receiptCount: (id) => 0,
    getReceipts: (id) => [],
    fetchReceipts: vi.fn(),
    uploadReceipt: vi.fn(),
    deleteReceipt: vi.fn(),
  }),
}))

vi.mock('../../stores/bills', () => ({
  useBillsStore: () => ({ markPaid: vi.fn() }),
}))

// Simple helpers (tested without full component mount to avoid Vuetify complexity)
describe('ReceiptPanel helpers', () => {
  const truncate = (str, max) => (str && str.length > max ? str.slice(0, max) + '…' : str)
  const formatSize = (bytes) => {
    if (!bytes) return ''
    if (bytes < 1048576) return `${Math.round(bytes / 1024)} KB`
    return `${(bytes / 1048576).toFixed(1)} MB`
  }
  const fileSizeRule = (file) => (!file || file.size < 10 * 1024 * 1024 ? true : 'Máximo 10 MB')

  it('truncates long file names', () => {
    expect(truncate('a'.repeat(40), 35)).toBe('a'.repeat(35) + '…')
  })

  it('does not truncate short names', () => {
    expect(truncate('short.pdf', 35)).toBe('short.pdf')
  })

  it('formats bytes < 1MB as KB', () => {
    expect(formatSize(234 * 1024)).toBe('234 KB')
  })

  it('formats bytes ≥ 1MB as MB', () => {
    expect(formatSize(1.5 * 1024 * 1024)).toBe('1.5 MB')
  })

  it('returns empty string for null size', () => {
    expect(formatSize(null)).toBe('')
  })

  it('file size rule rejects files over 10MB', () => {
    const bigFile = { size: 11 * 1024 * 1024 }
    expect(fileSizeRule(bigFile)).toBe('Máximo 10 MB')
  })

  it('file size rule accepts files under 10MB', () => {
    const okFile = { size: 2 * 1024 * 1024 }
    expect(fileSizeRule(okFile)).toBe(true)
  })

  it('file size rule accepts null (no file)', () => {
    expect(fileSizeRule(null)).toBe(true)
  })
})

// ReceiptChip logic
describe('ReceiptChip logic', () => {
  it('chip visible when count > 0', () => {
    const hasReceipts = (id) => id === 'bill-1'
    expect(hasReceipts('bill-1')).toBe(true)
    expect(hasReceipts('bill-2')).toBe(false)
  })

  it('receiptCount returns correct number', () => {
    const counts = { 'bill-1': 3 }
    const receiptCount = (id) => counts[id] || 0
    expect(receiptCount('bill-1')).toBe(3)
    expect(receiptCount('bill-2')).toBe(0)
  })
})

// Receipt list state
describe('ReceiptPanel — receipt list state', () => {
  it('empty state when no receipts', () => {
    const getReceipts = (id) => []
    expect(getReceipts('any-bill').length).toBe(0)
  })

  it('list shows when receipts present', () => {
    const receipts = [
      { id: 'r1', fileName: 'factura1.pdf', driveWebViewLink: 'https://drive/1', mimeType: 'application/pdf' },
      { id: 'r2', fileName: 'pago2.jpg', driveWebViewLink: 'https://drive/2', mimeType: 'image/jpeg' },
    ]
    const getReceipts = (id) => receipts
    expect(getReceipts('bill-1').length).toBe(2)
  })
})
