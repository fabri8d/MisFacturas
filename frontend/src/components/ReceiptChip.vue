<template>
  <v-chip
    v-if="hasReceipts(billId)"
    size="x-small"
    color="primary"
    variant="tonal"
    prepend-icon="mdi-paperclip"
    style="cursor:pointer"
    @click.stop="$emit('view', billId)"
  >
    {{ receiptCount(billId) }}
  </v-chip>
</template>

<script setup>
import { useReceiptsStore } from '../stores/receipts'

defineProps({ billId: { type: String, required: true } })
defineEmits(['view'])

const { hasReceipts, receiptCount } = useReceiptsStore()
</script>
