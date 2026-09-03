<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseSelect from '@/components/common/BaseSelect.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { trackedConceptsApi, severityClassesApi } from '../api/detection.api'
import type { TrackedConcept, SeverityClass } from '../types'
import { required, runValidators } from '@/utils/validators'
import type { ApiError } from '@/types'
import { Lock } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
  item?: TrackedConcept | null
}>()

const emit = defineEmits<{ close: []; saved: [item: TrackedConcept] }>()

const isBuiltin = computed(() => props.item?.source === 'BUILTIN')

const name = ref('')
const description = ref('')
const pattern = ref('')
const severityClass = ref('')

const errors = ref<Record<string, string | null>>({})
const formError = ref<string | null>(null)
const isSubmitting = ref(false)

const severityOptions = ref<SeverityClass[]>([])
const severityError = ref<string | null>(null)

async function loadSeverityClasses() {
  severityError.value = null
  try {
    severityOptions.value = await severityClassesApi.list()
  } catch {
    severityError.value = 'Could not load severity classes.'
  }
}

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) return
    errors.value = {}
    formError.value = null
    name.value = props.item?.name ?? ''
    description.value = props.item?.description ?? ''
    pattern.value = props.item?.pattern ?? ''
    severityClass.value = props.item?.severity_class ? String(props.item.severity_class) : ''
    loadSeverityClasses()
  },
)

function validateName() {
  errors.value.name = runValidators(name.value, [required()])
}
function validatePattern() {
  const base = runValidators(pattern.value, [required()])
  if (base) {
    errors.value.pattern = base
    return
  }
  try {
    new RegExp(pattern.value)
    errors.value.pattern = null
  } catch {
    errors.value.pattern = 'Not a valid regular expression.'
  }
}

async function handleSubmit() {
  formError.value = null
  validateName()
  validatePattern()
  if (errors.value.name || errors.value.pattern) return

  const payload = {
    name: name.value.trim(),
    description: description.value.trim(),
    pattern: pattern.value.trim(),
    severity_class: severityClass.value ? Number(severityClass.value) : null,
  }

  isSubmitting.value = true
  try {
    const { data } = props.item
      ? await trackedConceptsApi.update(props.item.id, payload)
      : await trackedConceptsApi.create(payload)
    emit('saved', data)
    emit('close')
  } catch (err) {
    const apiErr = err as ApiError
    if (apiErr.fieldErrors) {
      for (const [field, msgs] of Object.entries(apiErr.fieldErrors)) errors.value[field] = msgs[0]
    } else {
      formError.value = apiErr.message || 'Could not save this tracked concept.'
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <BaseModal :open="open" :title="item ? 'Edit Tracked Concept' : 'Add Tracked Concept'" @close="emit('close')">
    <div v-if="isBuiltin" class="space-y-3">
      <p class="flex items-center gap-2 text-sm text-status-warning bg-status-warning-bg border border-status-warning/20 rounded-md px-3 py-2">
        <Lock class="w-4 h-4 shrink-0" />
        This is a built-in tracked concept and cannot be modified.
      </p>
      <dl class="text-sm space-y-2">
        <div><dt class="text-text-secondary">Name</dt><dd class="text-text-primary">{{ item?.name }}</dd></div>
        <div><dt class="text-text-secondary">Description</dt><dd class="text-text-primary">{{ item?.description || '—' }}</dd></div>
        <div><dt class="text-text-secondary">Pattern</dt><dd class="text-text-primary font-mono text-xs">{{ item?.pattern }}</dd></div>
      </dl>
      <div class="flex justify-end pt-2">
        <BaseButton variant="secondary" @click="emit('close')">Close</BaseButton>
      </div>
    </div>

    <form v-else class="space-y-4" @submit.prevent="handleSubmit">
      <ErrorAlert v-if="formError" :message="formError" class="mb-1" />
      <p v-if="severityError" class="text-xs text-status-warning">{{ severityError }}</p>

      <BaseInput id="concept-name" v-model="name" label="Name" :error="errors.name" :disabled="isSubmitting" @blur="validateName" />

      <div>
        <label for="concept-description" class="block text-sm font-medium text-text-primary mb-1">Description</label>
        <textarea
          id="concept-description"
          v-model="description"
          rows="3"
          :disabled="isSubmitting"
          class="w-full rounded-md border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500 disabled:bg-surface-sunken disabled:text-text-muted"
        />
      </div>

      <BaseInput
        id="concept-pattern"
        v-model="pattern"
        label="Pattern (regex)"
        placeholder="e.g. no\\s+ip\\s+domain-lookup"
        :error="errors.pattern"
        :disabled="isSubmitting"
        @blur="validatePattern"
      />

      <BaseSelect
        id="concept-severity"
        v-model="severityClass"
        label="Severity Class"
        placeholder="No severity assigned"
        :options="severityOptions.map((s) => ({ value: s.id, label: s.name }))"
        :disabled="isSubmitting"
      />

      <div class="flex justify-end gap-2 pt-2">
        <BaseButton type="button" variant="secondary" :disabled="isSubmitting" @click="emit('close')">Cancel</BaseButton>
        <BaseButton type="submit" :loading="isSubmitting">Save</BaseButton>
      </div>
    </form>
  </BaseModal>
</template>