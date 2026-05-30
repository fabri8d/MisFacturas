<template>
  <v-snackbar
    v-model="show"
    location="bottom center"
    :timeout="3500"
    :color="snackColor"
    rounded="lg"
    @update:model-value="(v) => !v && emit('close')"
  >
    {{ message }}
    <template #actions>
      <v-btn variant="text" icon="mdi-close" size="small" @click="emit('close')" />
    </template>
  </v-snackbar>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  message: { type: String, default: '' },
  type:    { type: String, default: 'info' },
  visible: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const show = computed(() => props.visible)

const snackColor = computed(() => ({
  success: 'success',
  error:   'error',
  warning: 'warning',
  info:    'info',
}[props.type] ?? 'info'))
</script>
