<script setup lang="ts">
import { useAppNotifications } from '@/composables/useAppNotifications'
import { CheckCircle2, X, XCircle } from 'lucide-vue-next'

const { notifications, dismiss } = useAppNotifications()
</script>

<template>
  <div class="pointer-events-none fixed right-4 top-4 z-[100] flex w-[min(28rem,calc(100vw-2rem))] flex-col gap-2" aria-live="polite" aria-relevant="additions">
    <TransitionGroup name="toast">
      <section
        v-for="notification in notifications"
        :key="notification.id"
        class="pointer-events-auto flex items-start gap-3 border bg-surface-raised p-4 shadow-lg"
        :class="notification.tone === 'success' ? 'border-status-healthy/40' : 'border-status-critical/40'"
        :role="notification.tone === 'error' ? 'alert' : 'status'"
      >
        <CheckCircle2 v-if="notification.tone === 'success'" class="mt-0.5 h-5 w-5 shrink-0 text-status-healthy" />
        <XCircle v-else class="mt-0.5 h-5 w-5 shrink-0 text-status-critical" />
        <div class="min-w-0 flex-1">
          <h2 class="text-sm font-semibold text-text-primary">{{ notification.title }}</h2>
          <p class="mt-1 whitespace-pre-wrap break-words text-xs leading-5 text-text-secondary">{{ notification.message }}</p>
        </div>
        <button type="button" class="shrink-0 rounded p-1 text-text-muted hover:bg-surface-sunken hover:text-text-primary" title="Dismiss notification" @click="dismiss(notification.id)">
          <X class="h-4 w-4" />
        </button>
      </section>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active,
.toast-move {
  transition: opacity 180ms ease, transform 180ms ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>