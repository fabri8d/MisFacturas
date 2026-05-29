<script setup>
/**
 * StatCard — Tarjeta de estadística.
 * @prop {string} label - Etiqueta del stat
 * @prop {number} amount - Monto a mostrar
 * @prop {'default'|'success'|'danger'|'warning'} variant - Color
 */
defineProps({
  label:   { type: String,  required: true },
  amount:  { type: Number,  required: true },
  variant: { type: String,  default: 'default' },
})

const fmt = (n) =>
  new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(n)
</script>

<template>
  <div class="stat-card" :class="variant">
    <span class="label">{{ label }}</span>
    <span class="amount">{{ fmt(amount) }}</span>
  </div>
</template>

<style scoped>
.stat-card {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 0; /* permite que flex items se encojan por debajo de su contenido */
}
.label  { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; }
.amount {
  font-size: clamp(0.8rem, 3.5vw, 1.25rem); /* escala con el viewport en mobile */
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.stat-card.success .amount { color: var(--success); }
.stat-card.danger  .amount { color: var(--danger);  }
.stat-card.warning .amount { color: var(--warning); }
</style>
