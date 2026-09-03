<script setup lang="ts">
import { ref, watch } from 'vue'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { severityClassesApi } from '../api/detection.api'
import type { SeverityClass } from '../types'
import { required, numberRange, runValidators } from '@/utils/validators'
import type { ApiError } from '@/types'

const props = defineProps<{
  open: boolean
  item?: SeverityClass | null
}>()

const emit = defineEmits<{ close: []; saved: [item: SeverityClass] }>()

const name = ref('')
const rank = ref('')
const errors = ref<Record<string, string | null>>({})
const formError = ref<string | null>(null)
const isSubmitting = ref(false)

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) return
    errors.value = {}
    formError.value = null
    name.value = props.item?.name ?? ''
    rank.value = props.item ? String(props.item.rank) : ''
  },
)

function validateName() {
  errors.value.name = runValidators(name.value, [required()])
}
function validateRank() {
  errors.value.rank = runValidators(rank.value, [required(), numberRange(1, 100)])
}

async function handleSubmit() {
  formError.value = null
  validateName()
  validateRank()
  if (errors.value.name || errors.value.rank) return

  const payload = { name: name.value.trim(), rank: Number(rank.value) }

  isSubmitting.value = true
  try {
    const { data } = props.item
      ? await severityClassesApi.update(props.item.id, payload)
      : await severityClassesApi.create(payload)
    emit('saved', data)
    emit('close')
  } catch (err) {
    const apiErr = err as ApiError
    if (apiErr.fieldErrors) {
      for (const [field, msgs] of Object.entries(apiErr.fieldErrors)) errors.value[field] = msgs[0]
    } else {
      formError.value = apiErr.message || 'Could not save this severity class.'
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <BaseModal :open="open" :title="item ? 'Edit Severity Class' : 'Add Severity Class'" @close="emit('close')">
    <ErrorAlert v-if="formError" :message="formError" class="mb-4" />
    <form class="space-y-4" @submit.prevent="handleSubmit">
      <BaseInput id="severity-name" v-model="name" label="Name" :error="errors.name" :disabled="isSubmitting" @blur="validateName" />
      <BaseInput
        id="severity-rank"
        v-model="rank"
        label="Rank"
        type="number"
        placeholder="Higher number = higher severity"
        :error="errors.rank"
        :disabled="isSubmitting"
        @blur="validateRank"
      />
      <div class="flex justify-end gap-2 pt-2">
        <BaseButton type="button" variant="secondary" :disabled="isSubmitting" @click="emit('close')">Cancel</BaseButton>
        <BaseButton type="submit" :loading="isSubmitting">Save</BaseButton>
      </div>
    </form>
  </BaseModal>
</template>