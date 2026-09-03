<script setup lang="ts">
defineProps<{
  message: string
}>()
</script>

<template>
  <div
    class="flex items-start gap-2 rounded-md bg-status-critical-bg border border-status-critical/20 px-3 py-2 text-sm text-status-critical"
    role="alert"
  >
    <svg class="h-4 w-4 mt-0.5 shrink-0" viewBox="0 0 20 20" fill="currentColor">
      <path
        fill-rule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zm-1-9a1 1 0 112 0v3a1 1 0 11-2 0V9zm1-4a1 1 0 100 2 1 1 0 000-2z"
        clip-rule="evenodd"
      />
    </svg>
    <span>{{ message }}</span>
  </div>
</template>