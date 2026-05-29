<script setup>
/**
 * BillRow — Fila de factura con estado visual y acciones.
 * @prop {Object}  bill       - Objeto factura
 * @prop {boolean} showActions - Muestra botones editar/eliminar
 * @emit {void} toggle  - Solicita alternar estado de pago
 * @emit {void} edit    - Solicita navegar a edición
 * @emit {void} delete  - Solicita eliminar
 */
import { computed } from 'vue'
import { CATEGORIES } from '../constants/categories'

const props = defineProps({
  bill:        { type: Object,  required: true },
  showActions: { type: Boolean, default: false },
})
const emit = defineEmits(['toggle', 'edit', 'delete'])

const fmt = (n) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(n)

const fmtDate = (s) => {
  if (!s) return ''
  const [y, m, d] = s.split('-')
  return `${d}/${m}/${y}`
}

/** Estado calculado a partir de isPaid y dueDate */
const status = computed(() => {
  if (props.bill.isPaid) return { label: 'Pagada', cls: 'paid' }
  const today = new Date().toISOString().slice(0, 10)
  if (props.bill.dueDate < today) return { label: 'Vencida', cls: 'overdue' }
  const diffDays = Math.ceil(
    (new Date(props.bill.dueDate) - new Date(today)) / 86400000,
  )
  if (diffDays <= 3) return { label: 'Urgente', cls: 'urgent' }
  return { label: 'Pendiente', cls: 'pending' }
})

const cat = computed(() => CATEGORIES[props.bill.category] ?? CATEGORIES.otro)
</script>

<template>
  <div class="bill-row">
    <button class="check" :class="status.cls" @click="emit('toggle')" :title="status.label">
      <span v-if="bill.isPaid">✓</span>
      <span v-else class="circle" />
    </button>

    <div class="info">
      <span class="name">{{ bill.name }}</span>
      <span class="meta">
        {{ cat.emoji }} {{ cat.label }} · {{ fmtDate(bill.dueDate) }}
      </span>
    </div>

    <div class="right">
      <span class="amount">{{ fmt(bill.amount) }}</span>
      <span class="badge" :class="status.cls">{{ status.label }}</span>
    </div>

    <div v-if="showActions" class="actions">
      <button class="icon-btn" @click="emit('edit')" title="Editar">✏️</button>
      <button class="icon-btn danger" @click="emit('delete')" title="Eliminar">🗑️</button>
    </div>
  </div>
</template>

<style scoped>
.bill-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  transition: background 0.15s;
}
.bill-row:hover { background: var(--surface-2); }

.check {
  width: 32px; height: 32px;
  border-radius: 50%;
  border: 2px solid var(--border);
  background: transparent;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  font-size: 1rem;
  transition: all 0.15s;
}
.check.paid    { border-color: var(--success); color: var(--success); background: rgba(74,222,128,0.1); }
.check.overdue { border-color: var(--danger);  color: var(--danger); }
.check.urgent  { border-color: var(--warning); color: var(--warning); }
.circle { width: 10px; height: 10px; border-radius: 50%; background: var(--border); }

.info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.name { font-size: 0.9rem; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.meta { font-size: 0.75rem; color: var(--text-muted); }

.right { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
.amount { font-size: 0.9rem; font-weight: 600; }

.badge {
  font-size: 0.65rem; padding: 2px 6px; border-radius: 99px; font-weight: 600;
}
.badge.paid    { background: rgba(74,222,128,0.15);  color: var(--success); }
.badge.overdue { background: rgba(248,113,113,0.15); color: var(--danger); }
.badge.urgent  { background: rgba(251,191,36,0.15);  color: var(--warning); }
.badge.pending { background: var(--surface-3); color: var(--text-muted); }

.actions { display: flex; flex-direction: column; gap: 4px; }
.icon-btn { background: transparent; color: var(--text-muted); font-size: 0.9rem; padding: 4px; border-radius: 6px; }
.icon-btn:hover { background: var(--surface-3); }
.icon-btn.danger:hover { color: var(--danger); }
</style>
