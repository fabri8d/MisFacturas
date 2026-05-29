<script setup>
/**
 * ProgressBar — Barra de progreso de pagos del mes.
 * @prop {number} paid   - Monto pagado
 * @prop {number} total  - Monto total
 */
import { computed } from 'vue'

const props = defineProps({
  paid:  { type: Number, required: true },
  total: { type: Number, required: true },
})

const pct = computed(() =>
  props.total > 0 ? Math.min(100, Math.round((props.paid / props.total) * 100)) : 0,
)
</script>

<template>
  <div class="progress-wrap">
    <div class="progress-header">
      <span>Pagado</span>
      <span>{{ pct }}%</span>
    </div>
    <div class="bar-bg">
      <div class="bar-fill" :style="{ width: pct + '%' }" />
    </div>
  </div>
</template>

<style scoped>
.progress-wrap { display: flex; flex-direction: column; gap: 6px; }
.progress-header { display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-muted); }
.bar-bg { height: 8px; background: var(--surface-3); border-radius: 99px; overflow: hidden; }
.bar-fill { height: 100%; background: var(--success); border-radius: 99px; transition: width 0.4s ease; }
</style>
