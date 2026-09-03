<script setup lang="ts">
import { ref, watch } from 'vue'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { detectionApi, trackedConceptsApi } from '../api/detection.api'
import type { DetectionProfile, TrackedConcept } from '../types'
import { required, runValidators } from '@/utils/validators'
import type { ApiError } from '@/types'

const props = defineProps<{
  open: boolean
  item?: DetectionProfile | null
}>()

const emit = defineEmits<{ close: []; saved: [item: DetectionProfile] }>()

const name = ref('')
const selectedConcepts = ref<Set<number>>(new Set())
const errors = ref<Record<string, string | null>>({})
const formError = ref<string | null>(null)
const isSubmitting = ref(false)

const concepts = ref<TrackedConcept[]>([])
const conceptsError = ref<string | null>(null)

async function loadConcepts() {
  conceptsError.value = null
  try {
    concepts.value = await trackedConceptsApi.list()
  } catch {
    conceptsError.value = 'Could not load tracked concepts.'
  }
}

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) return
    errors.value = {}
    formError.value = null
    name.value = props.item?.name ?? ''
    selectedConcepts.value = new Set(props.item?.tracked_concepts ?? [])
    loadConcepts()
  },
)

function toggleConcept(id: number) {
  if (selectedConcepts.value.has(id)) selectedConcepts.value.delete(id)
  else selectedConcepts.value.add(id)
}

function validateName() {
  errors.value.name = runValidators(name.value, [required()])
}

async function handleSubmit() {
  formError.value = null
  validateName()
  if (errors.value.name) return

  const payload = { name: name.value.trim(), tracked_concepts: [...selectedConcepts.value] }

  isSubmitting.value = true
  try {
    const { data } = props.item ? await detectionApi.update(props.item.id, payload) : await detectionApi.create(payload)
    emit('saved', data)
    emit('close')
  } catch (err) {
    const apiErr = err as ApiError
    if (apiErr.fieldErrors) {
      for (const [field, msgs] of Object.entries(apiErr.fieldErrors)) errors.value[field] = msgs[0]
    } else {
      formError.value = apiErr.message || 'Could not save this profile.'
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <BaseModal :open="open" :title="item ? 'Edit Detection Profile' : 'Add Detection Profile'" @close="emit('close')">
    <ErrorAlert v-if="formError" :message="formError" class="mb-4" />
    <form class="space-y-4" @submit.prevent="handleSubmit">
      <BaseInput id="profile-name" v-model="name" label="Name" :error="errors.name" :disabled="isSubmitting" @blur="validateName" />

      <div>
        <p class="block text-sm font-medium text-text-primary mb-1">Tracked Concepts</p>
        <p v-if="conceptsError" class="text-xs text-status-warning mb-2">{{ conceptsError }}</p>
        <div class="border border-border rounded-md max-h-56 overflow-y-auto divide-y divide-border">
          <label
            v-for="concept in concepts"
            :key="concept.id"
            class="flex items-start gap-2 px-3 py-2 text-sm hover:bg-surface-sunken cursor-pointer"
          >
            <input
              type="checkbox"
              class="mt-0.5"
              :checked="selectedConcepts.has(concept.id)"
              :disabled="isSubmitting"
              @change="toggleConcept(concept.id)"
            />
            <span>
              <span class="text-text-primary">{{ concept.name }}</span>
              <span v-if="concept.source === 'BUILTIN'" class="ml-2 text-xs text-text-muted">Built-in</span>
            </span>
          </label>
          <p v-if="concepts.length === 0" class="px-3 py-2 text-sm text-text-muted">No tracked concepts yet.</p>
        </div>
      </div>

      <div class="flex justify-end gap-2 pt-2">
        <BaseButton type="button" variant="secondary" :disabled="isSubmitting" @click="emit('close')">Cancel</BaseButton>
        <BaseButton type="submit" :loading="isSubmitting">Save</BaseButton>
      </div>
    </form>
  </BaseModal>
</template>