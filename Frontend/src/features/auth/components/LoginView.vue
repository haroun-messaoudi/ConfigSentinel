<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.store'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { required, runValidators } from '@/utils/validators'
import type { ApiError } from '@/types'
import { ShieldCheck, GitCompareArrows, Bell, Server } from 'lucide-vue-next'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const form = reactive({ username: '', password: '' })
const fieldErrors = reactive<{ username: string | null; password: string | null }>({
  username: null,
  password: null,
})
const formError = ref<string | null>(null)
const isSubmitting = ref(false)

const features = [
  { icon: Server, text: 'Continuous polling of your network devices' },
  { icon: GitCompareArrows, text: 'Structural diffing on every config change' },
  { icon: ShieldCheck, text: 'Configurable detection profiles and severity tiers' },
  { icon: Bell, text: 'Real-time alerts on drift that matters' },
]

function validateField(field: 'username' | 'password') {
  fieldErrors[field] = runValidators(form[field], [required()])
}
function validateAll(): boolean {
  validateField('username')
  validateField('password')
  return !fieldErrors.username && !fieldErrors.password
}

async function handleSubmit() {
  formError.value = null
  if (!validateAll()) return
  isSubmitting.value = true
  try {
    await auth.login({ username: form.username, password: form.password })
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.push(redirect)
  } catch (err) {
    const apiError = err as ApiError
    if (apiError.status === 401) {
      formError.value = 'Incorrect username or password.'
    } else if (apiError.status === 0) {
      formError.value = 'Cannot reach the server. Check your connection and try again.'
    } else if (apiError.fieldErrors) {
      if (apiError.fieldErrors.username) fieldErrors.username = apiError.fieldErrors.username[0]
      if (apiError.fieldErrors.password) fieldErrors.password = apiError.fieldErrors.password[0]
      if (!apiError.fieldErrors.username && !apiError.fieldErrors.password) {
        formError.value = apiError.message
      }
    } else {
      formError.value = apiError.message || 'Something went wrong. Please try again.'
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex bg-chrome-bg">
    <!-- Branding panel — hidden below lg so mobile just gets the form, no
         squeezed/broken layout. -->
    <div class="hidden lg:flex lg:w-1/2 xl:w-3/5 bg-chrome-bg-hover border-r border-chrome-border flex-col justify-center px-16 relative overflow-hidden">
      <div class="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-brand-500/10 blur-3xl" />
      <div class="absolute -bottom-32 -left-16 w-80 h-80 rounded-full bg-status-healthy/10 blur-3xl" />

      <div class="relative">
        <h1 class="text-3xl font-bold text-chrome-text-strong mb-3">ConfigSentinel</h1>
        <p class="text-base text-chrome-text max-w-md mb-10">
          Automated network configuration drift detection — catch unauthorized or risky changes before they become incidents.
        </p>

        <div class="space-y-5">
          <div v-for="feature in features" :key="feature.text" class="flex items-center gap-3">
            <span class="flex items-center justify-center w-9 h-9 rounded-lg bg-brand-500/10 text-brand-600 shrink-0">
              <component :is="feature.icon" class="w-4.5 h-4.5" />
            </span>
            <span class="text-sm text-chrome-text">{{ feature.text }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Login form -->
    <div class="flex-1 flex items-center justify-center px-4 py-12">
      <div class="w-full max-w-sm">
        <div class="text-center mb-8 lg:hidden">
          <h1 class="text-2xl font-semibold text-chrome-text-strong">ConfigSentinel</h1>
          <p class="text-sm text-chrome-text mt-1">Network configuration monitoring</p>
        </div>
        <div class="hidden lg:block mb-8">
          <h2 class="text-xl font-semibold text-chrome-text-strong">Sign in</h2>
          <p class="text-sm text-chrome-text mt-1">Enter your credentials to access the console.</p>
        </div>

        <form
          novalidate
          class="bg-surface-raised border border-border rounded-lg shadow-lg p-6 space-y-4"
          @submit.prevent="handleSubmit"
        >
          <ErrorAlert v-if="formError" :message="formError" />
          <BaseInput
            id="username"
            v-model="form.username"
            label="Username"
            autocomplete="username"
            :error="fieldErrors.username"
            :disabled="isSubmitting"
            @blur="validateField('username')"
          />
          <BaseInput
            id="password"
            v-model="form.password"
            label="Password"
            type="password"
            autocomplete="current-password"
            :error="fieldErrors.password"
            :disabled="isSubmitting"
            @blur="validateField('password')"
          />
          <BaseButton type="submit" class="w-full" :loading="isSubmitting">
            {{ isSubmitting ? 'Signing in…' : 'Sign in' }}
          </BaseButton>
        </form>
      </div>
    </div>
  </div>
</template>