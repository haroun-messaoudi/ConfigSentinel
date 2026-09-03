<script setup lang="ts">
defineProps<{
  modelValue: string
  label: string
  id: string
  type?: string
  autocomplete?: string
  placeholder?: string
  error?: string | null
  disabled?: boolean
}>()

defineEmits<{
  'update:modelValue': [value: string]
  blur: []
}>()
</script>

<template>
  <div>
    <label :for="id" class="block text-sm font-medium text-text-primary mb-1">
      {{ label }}
    </label>
    <input
      :id="id"
      :type="type ?? 'text'"
      :autocomplete="autocomplete"
      :placeholder="placeholder"
      :disabled="disabled"
      :aria-invalid="!!error"
      :aria-describedby="error ? `${id}-error` : undefined"
      :value="modelValue"
      class="w-full rounded-md border bg-surface-raised px-3 py-2 text-sm text-text-primary transition-colors focus:outline-none focus:ring-2 disabled:bg-surface-sunken disabled:text-text-muted"
      :class="
        error
          ? 'border-status-critical focus:ring-status-critical/40'
          : 'border-border focus:ring-brand-500/40 focus:border-brand-500'
      "
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      @blur="$emit('blur')"
    />
    <p v-if="error" :id="`${id}-error`" class="mt-1 text-xs text-status-critical">
      {{ error }}
    </p>
  </div>
</template>