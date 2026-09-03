<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseSelect from '@/components/common/BaseSelect.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { devicesApi, deviceTypesApi } from '../api/devices.api'
import { detectionApi } from '@/features/detection/api/detection.api'
import type { Device, DeviceFormPayload, DeviceTypeOption } from '../types'
import type { DetectionProfile } from '@/features/detection/types'
import { required, minLength, pattern, numberRange, runValidators } from '@/utils/validators'
import type { ApiError } from '@/types'
import BaseButton from '@/components/common/BaseButton.vue'

const props = defineProps<{
  open: boolean
  mode: 'create' | 'edit'
  device?: Device | null
}>()

const emit = defineEmits<{
  close: []
  saved: [device: Device]
}>()

const HOSTNAME_PATTERN = /^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*$/

const name = ref('')
const hostname = ref('')
const managementIp = ref('')
const port = ref('22')
const deviceType = ref('')
const username = ref('')
const password = ref('')
const enableSecret = ref('')
const pollInterval = ref('5')
const detectionProfile = ref('')

const errors = ref<Record<string, string | null>>({})
const formError = ref<string | null>(null)
const isSubmitting = ref(false)

const profiles = ref<DetectionProfile[]>([])
const profilesError = ref<string | null>(null)
const profileOptions = computed(() => profiles.value.map((p) => ({ value: String(p.id), label: p.name })))

async function loadProfiles() {
  profilesError.value = null
  try {
    profiles.value = await detectionApi.list()
  } catch {
    profilesError.value = 'Could not load detection profiles. You can still save without changing this field.'
  }
}

const deviceTypeOptions = ref<DeviceTypeOption[]>([])
const deviceTypesLoading = ref(false)
const deviceTypesError = ref<string | null>(null)

async function loadDeviceTypes() {
  deviceTypesError.value = null
  deviceTypesLoading.value = true
  try {
    deviceTypeOptions.value = await deviceTypesApi.list()
  } catch {
    deviceTypesError.value = 'Could not load device types. Please close and try again.'
  } finally {
    deviceTypesLoading.value = false
  }
}

// device_type is required to submit, unlike the optional detection profile —
// block submission entirely if we don't have valid options to choose from.
const canSubmit = computed(() => !deviceTypesError.value && !deviceTypesLoading.value)

function resetForm() {
  errors.value = {}
  formError.value = null

  if (props.mode === 'edit' && props.device) {
    name.value = props.device.name
    hostname.value = props.device.hostname
    managementIp.value = props.device.management_ip
    port.value = String(props.device.port)
    deviceType.value = props.device.device_type
    username.value = props.device.username
    password.value = ''
    enableSecret.value = ''
    pollInterval.value = String(props.device.poll_interval_minutes)
    detectionProfile.value = props.device.detection_profile ? String(props.device.detection_profile) : ''
  } else {
    name.value = ''
    hostname.value = ''
    managementIp.value = ''
    port.value = '22'
    deviceType.value = ''
    username.value = ''
    password.value = ''
    enableSecret.value = ''
    pollInterval.value = '5'
    detectionProfile.value = ''
  }
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      resetForm()
      loadProfiles()
      loadDeviceTypes()
    }
  },
  { immediate: true }
)

function validateField(field: string) {
  switch (field) {
    case 'name':
      errors.value.name = runValidators(name.value, [required(), minLength(3)])
      break
    case 'hostname':
      errors.value.hostname = runValidators(hostname.value, [
        required(),
        pattern(HOSTNAME_PATTERN, 'Enter a valid hostname.'),
      ])
      break
    case 'management_ip':
      errors.value.management_ip = runValidators(managementIp.value, [required()])
      break
    case 'port':
      errors.value.port = runValidators(port.value, [required(), numberRange(1, 65535)])
      break
    case 'device_type':
      errors.value.device_type = runValidators(deviceType.value, [required('Select a device type.')])
      break
    case 'username':
      errors.value.username = runValidators(username.value, [required()])
      break
    case 'password':
      errors.value.password =
        props.mode === 'create'
          ? runValidators(password.value, [required(), minLength(8)])
          : password.value
            ? runValidators(password.value, [minLength(8)])
            : null
      break
    // enable_secret is intentionally not validated with minLength/required —
    // it's optional at any length, including empty (empty explicitly clears
    // it server-side; see DeviceFormModal submit handling below).
    case 'poll_interval_minutes':
      errors.value.poll_interval_minutes = runValidators(pollInterval.value, [
        required(),
        numberRange(1, 10080, 'Must be at least 1 minute.'),
      ])
      break
  }
}

function validateAll() {
  ;['name', 'hostname', 'management_ip', 'port', 'device_type', 'username', 'password', 'poll_interval_minutes'].forEach(
    validateField,
  )
  return Object.values(errors.value).every((e) => !e)
}

async function handleSubmit() {
  formError.value = null
  if (!canSubmit.value) {
    formError.value = deviceTypesError.value || 'Please wait for the form to finish loading.'
    return
  }
  if (!validateAll()) return

  const payload: DeviceFormPayload = {
    name: name.value.trim(),
    hostname: hostname.value.trim(),
    management_ip: managementIp.value.trim(),
    port: Number(port.value),
    device_type: deviceType.value as DeviceFormPayload['device_type'],
    username: username.value.trim(),
    poll_interval_minutes: Number(pollInterval.value),
    detection_profile: detectionProfile.value ? Number(detectionProfile.value) : null,
  }
  if (password.value) payload.password = password.value
  // Only send enable_secret if the user actually touched the field.
  // In edit mode, an untouched field must NOT overwrite an existing
  // secret with an empty string — only an explicit clear should do that.
  if (enableSecret.value !== '') payload.enable_secret = enableSecret.value

  isSubmitting.value = true
  try {
    const { data } =
      props.mode === 'create'
        ? await devicesApi.create(payload)
        : await devicesApi.update(props.device!.id, payload)
    emit('saved', data)
    emit('close')
  } catch (err) {
    const apiErr = err as ApiError
    if (apiErr.fieldErrors) {
      for (const [field, msgs] of Object.entries(apiErr.fieldErrors)) {
        errors.value[field] = msgs[0]
      }
    } else {
      formError.value = apiErr.message || 'Could not save this device. Please try again.'
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <BaseModal :open="open" :title="mode === 'create' ? 'Add Device' : 'Edit Device'" @close="emit('close')">
    <ErrorAlert v-if="formError" :message="formError" class="mb-4" />
    <ErrorAlert v-if="deviceTypesError" :message="deviceTypesError" class="mb-4" />
    <p v-if="profilesError" class="mb-4 text-xs text-amber-600">{{ profilesError }}</p>

    <form class="space-y-4" @submit.prevent="handleSubmit">
      <BaseInput
        id="device-name"
        v-model="name"
        label="Name"
        :error="errors.name"
        :disabled="isSubmitting"
        @blur="validateField('name')"
      />
      <BaseInput
        id="device-hostname"
        v-model="hostname"
        label="Hostname"
        :error="errors.hostname"
        :disabled="isSubmitting"
        @blur="validateField('hostname')"
      />
      <BaseInput
        id="device-ip"
        v-model="managementIp"
        label="Management IP"
        :error="errors.management_ip"
        :disabled="isSubmitting"
        @blur="validateField('management_ip')"
      />
      <div class="grid grid-cols-2 gap-4">
        <BaseInput
          id="device-port"
          v-model="port"
          label="Port"
          type="number"
          :error="errors.port"
          :disabled="isSubmitting"
          @blur="validateField('port')"
        />
        <BaseInput
          id="device-poll-interval"
          v-model="pollInterval"
          label="Poll Interval (min)"
          type="number"
          :error="errors.poll_interval_minutes"
          :disabled="isSubmitting"
          @blur="validateField('poll_interval_minutes')"
        />
      </div>
      <BaseSelect
        id="device-type"
        v-model="deviceType"
        label="Device Type"
        :placeholder="deviceTypesLoading ? 'Loading device types…' : 'Select a device type'"
        :options="deviceTypeOptions"
        :error="errors.device_type"
        :disabled="isSubmitting || deviceTypesLoading || !!deviceTypesError"
        @blur="validateField('device_type')"
      />
      <BaseSelect
        id="device-profile"
        v-model="detectionProfile"
        label="Detection Profile"
        placeholder="No profile assigned"
        :options="profileOptions"
        :disabled="isSubmitting || !!profilesError"
      />
      <BaseInput
        id="device-username"
        v-model="username"
        label="SSH Username"
        autocomplete="off"
        :error="errors.username"
        :disabled="isSubmitting"
        @blur="validateField('username')"
      />
      <BaseInput
        id="device-password"
        v-model="password"
        :label="mode === 'create' ? 'SSH Password' : 'SSH Password (leave blank to keep current)'"
        type="password"
        autocomplete="new-password"
        :error="errors.password"
        :disabled="isSubmitting"
        @blur="validateField('password')"
      />
      <BaseInput
        id="device-enable-secret"
        v-model="enableSecret"
        label="Enable Secret (optional — leave blank if the device doesn't need one)"
        type="password"
        autocomplete="new-password"
        :disabled="isSubmitting"
      />

      <div class="flex justify-end gap-2 pt-2">
        <BaseButton type="button" variant="secondary" :disabled="isSubmitting" @click="emit('close')">Cancel</BaseButton>
        <BaseButton type="submit" :loading="isSubmitting" :disabled="!canSubmit || isSubmitting">
          {{ isSubmitting ? 'Saving…' : mode === 'create' ? 'Add Device' : 'Save Changes' }}
        </BaseButton>
      </div>
    </form>
  </BaseModal>
</template>