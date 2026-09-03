<script setup lang="ts">
import { ref } from 'vue'
import BaseInput from '@/components/common/BaseInput.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { usersApi } from '@/features/users/api/users.api'
import { required, minLength, matches, runValidators } from '@/utils/validators'
import type { ApiError } from '@/types'

const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')

const oldError = ref<string | null>(null)
const newError = ref<string | null>(null)
const confirmError = ref<string | null>(null)
const formError = ref<string | null>(null)
const successMessage = ref('')

const isSubmitting = ref(false)

function validateOld() {
  oldError.value = runValidators(oldPassword.value, [required()])
}
function validateNew() {
  newError.value = runValidators(newPassword.value, [required(), minLength(8)])
  if (confirmPassword.value) validateConfirm()
}
function validateConfirm() {
  confirmError.value = runValidators(confirmPassword.value, [
    required(),
    matches(() => newPassword.value),
  ])
}

async function handleSubmit() {
  formError.value = null
  successMessage.value = ''

  validateOld()
  validateNew()
  validateConfirm()
  if (oldError.value || newError.value || confirmError.value) return

  isSubmitting.value = true
  try {
    await usersApi.changePassword({
      old_password: oldPassword.value,
      new_password: newPassword.value,
    })
    successMessage.value = 'Password updated successfully.'
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
  } catch (err) {
    const apiErr = err as ApiError
    if (apiErr.fieldErrors?.old_password) {
      oldError.value = apiErr.fieldErrors.old_password[0]
    } else if (apiErr.fieldErrors?.new_password) {
      newError.value = apiErr.fieldErrors.new_password[0]
    } else {
      formError.value = apiErr.message || 'Something went wrong. Please try again.'
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="max-w-md">
    <h2 class="text-xl font-semibold text-slate-900 mb-1">Change Password</h2>
    <p class="text-sm text-slate-500 mb-6">Update the password for your account.</p>

    <div class="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
      <ErrorAlert v-if="formError" :message="formError" class="mb-4" />
      <p v-if="successMessage" class="mb-4 text-sm text-emerald-600" role="status">
        {{ successMessage }}
      </p>

      <form class="space-y-4" @submit.prevent="handleSubmit">
        <BaseInput
          id="old-password"
          v-model="oldPassword"
          label="Current Password"
          type="password"
          autocomplete="current-password"
          :error="oldError"
          :disabled="isSubmitting"
          @blur="validateOld"
        />
        <BaseInput
          id="new-password"
          v-model="newPassword"
          label="New Password"
          type="password"
          autocomplete="new-password"
          :error="newError"
          :disabled="isSubmitting"
          @blur="validateNew"
        />
        <BaseInput
          id="confirm-password"
          v-model="confirmPassword"
          label="Confirm New Password"
          type="password"
          autocomplete="new-password"
          :error="confirmError"
          :disabled="isSubmitting"
          @blur="validateConfirm"
        />

        <button
          type="submit"
          class="w-full rounded-md bg-brand-500 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="isSubmitting"
        >
          {{ isSubmitting ? 'Updating…' : 'Update Password' }}
        </button>
      </form>
    </div>
  </div>
</template>