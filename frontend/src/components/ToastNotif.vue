<script setup>
/**
 * ToastNotif — Notificación tipo toast.
 * @prop {string} message - Texto a mostrar
 * @prop {'success'|'error'|'warning'|'info'} type - Tipo visual
 * @prop {boolean} visible - Controla visibilidad
 * @emit {void} close - Emitido cuando el toast se cierra
 */
import { watch } from 'vue'

const props = defineProps({
  message: { type: String, default: '' },
  type: { type: String, default: 'info' },
  visible: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

watch(
  () => props.visible,
  (val) => {
    if (val) setTimeout(() => emit('close'), 3500)
  },
)
</script>

<template>
  <Transition name="toast">
    <div v-if="visible" class="toast" :class="type" @click="emit('close')">
      {{ message }}
    </div>
  </Transition>
</template>

<style scoped>
.toast {
  position: fixed;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 20px;
  border-radius: var(--radius);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  z-index: 9999;
  max-width: 90vw;
  text-align: center;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}
.toast.success { background: var(--success); color: #000; }
.toast.error   { background: var(--danger);  color: #fff; }
.toast.warning { background: var(--warning); color: #000; }
.toast.info    { background: var(--info);    color: #000; }

.toast-enter-active, .toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateX(-50%) translateY(12px); }
</style>
