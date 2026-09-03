<script setup lang="ts">
defineProps<{
  open: boolean
  title: string
}>()

const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-slate-950/60" @click="emit('close')" />
      <div
        class="relative bg-surface-raised rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
        role="dialog"
        aria-modal="true"
      >
        <div class="flex items-center justify-between border-b border-border px-5 py-4">
          <h3 class="text-lg font-semibold text-text-primary">{{ title }}</h3>
          <button type="button" class="text-text-muted hover:text-text-primary" aria-label="Close" @click="emit('close')">
            <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path
                fill-rule="evenodd"
                d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
                clip-rule="evenodd"
              />
            </svg>
          </button>
        </div>
        <div class="px-5 py-4">
          <slot />
        </div>
      </div>
    </div>
  </Teleport>
</template>