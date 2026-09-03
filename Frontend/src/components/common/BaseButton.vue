<script setup lang="ts">
withDefaults(
  defineProps<{
    type?: 'button' | 'submit'
    variant?: 'primary' | 'secondary' | 'danger'
    loading?: boolean
    disabled?: boolean
  }>(),
  {
    type: 'button',
    variant: 'primary',
    loading: false,
    disabled: false,
  },
)

const variantClasses: Record<string, string> = {
  primary: 'bg-brand-500 text-white hover:bg-brand-600',
  secondary: 'bg-surface-raised text-text-primary border border-border hover:bg-surface-sunken',
  danger: 'bg-status-critical text-white hover:opacity-90',
}
</script>

<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    class="inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium py-2 px-4 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
    :class="variantClasses[variant]"
  >
    <svg v-if="loading" class="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
    <slot />
  </button>
</template>