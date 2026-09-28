<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseSelect from '@/components/common/BaseSelect.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { actionsApi } from '../api/actions.api'
import type { ActionDefinition, ActionParameter, ChangeRequestItem } from '../types'
import type { Device } from '@/features/devices/types'
import type { ApiError } from '@/types'
import { useAppNotifications } from '@/composables/useAppNotifications'
import { Terminal, ShieldCheck, CheckCircle, XCircle, Clock, AlertTriangle, Loader2 } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
  device: Device | null
  availableActions: ActionDefinition[]
  canConfirm: boolean
}>()

const emit = defineEmits<{
  close: []
  submitted: [changeRequestId: number]
}>()

type Stage = 'form' | 'review' | 'executing' | 'result'

const POLL_INTERVAL_MS = 2000
const MAX_POLL_ATTEMPTS = 30 // Switch to slower polling after about 60 seconds

const stage = ref<Stage>('form')
const selectedActionId = ref<number | string>('')
const paramValues = ref<Record<string, any>>({})
const submitting = ref(false)
const confirming = ref(false)
const errorMessage = ref<string | null>(null)
const pendingRequest = ref<ChangeRequestItem | null>(null)

const pollTimer = ref<ReturnType<typeof setTimeout> | null>(null)
const pollAttempts = ref(0)
const pollTimedOut = ref(false)
const { notify } = useAppNotifications()

const selectedAction = computed(() => {
  return props.availableActions.find((a) => a.id === Number(selectedActionId.value)) || null
})

const actionOptions = computed(() => {
  return props.availableActions.map((a) => ({ value: a.id, label: a.name }))
})

watch(selectedActionId, () => {
  paramValues.value = {}
  errorMessage.value = null
  if (selectedAction.value) {
    selectedAction.value.parameters.forEach((p: ActionParameter) => {
      if (p.data_type === 'BOOLEAN') {
        paramValues.value[p.name] = p.default_value ? p.default_value.toLowerCase() === 'true' : false
      } else if (p.default_value !== undefined && p.default_value !== '') {
        paramValues.value[p.name] = p.default_value
      }
    })
  }
})

const isFormValid = computed(() => {
  if (!selectedAction.value || !props.device) return false
  for (const param of selectedAction.value.parameters) {
    if (param.data_type === 'BOOLEAN') continue // always has a defined true/false value
    if (param.is_required && (!paramValues.value[param.name] || paramValues.value[param.name].toString().trim() === '')) {
      return false
    }
  }
  return true
})

async function handleSubmit() {
  if (!selectedAction.value || !props.device) return
  submitting.value = true
  errorMessage.value = null

  try {
    const res = await actionsApi.submitChangeRequest({
      device: props.device.id,
      action_definition: selectedAction.value.id,
      params: paramValues.value,
    })
    pendingRequest.value = res.data
    stage.value = props.canConfirm ? 'review' : 'result'
  } catch (err) {
    const apiErr = err as ApiError
    if (apiErr.fieldErrors) {
      const firstField = Object.values(apiErr.fieldErrors)[0]
      errorMessage.value = Array.isArray(firstField) ? firstField.join(' ') : String(firstField)
    } else {
      errorMessage.value = apiErr.message || 'Failed to submit change request.'
    }
  } finally {
    submitting.value = false
  }
}

function stopPolling() {
  if (pollTimer.value !== null) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

async function checkStatus() {
  if (!pendingRequest.value || stage.value !== 'executing') return

  try {
    const updated = await actionsApi.getChangeRequest(pendingRequest.value.id)
    pendingRequest.value = updated

    if (updated.status !== 'PENDING') {
      stopPolling()
      stage.value = 'result'
      const actionName = selectedAction.value?.name || updated.action_name
      const deviceName = props.device?.name || updated.device_name
      if (updated.status === 'SUCCESS') {
        notify({
          tone: 'success',
          title: 'Configuration change succeeded',
          message: `${actionName} was applied to ${deviceName}. Request #${updated.id} is saved in your change history.`,
        })
      } else {
        notify({
          tone: 'error',
          title: 'Configuration change failed',
          message: `${actionName} on ${deviceName} failed. ${updated.error_message || 'The device did not provide an error detail.'} Request #${updated.id} is saved in your change history.`,
        })
      }
      return
    }
  } catch {
    // Transient poll failure (brief network blip) — keep trying rather than
    // surfacing a scary error; MAX_POLL_ATTEMPTS below is the real backstop.
  }

  pollAttempts.value += 1
  if (pollAttempts.value >= MAX_POLL_ATTEMPTS) {
    pollTimedOut.value = true
  }
  pollTimer.value = setTimeout(() => void checkStatus(), pollTimedOut.value ? 5000 : POLL_INTERVAL_MS)
}

async function startPolling() {
  pollAttempts.value = 0
  pollTimedOut.value = false
  // Check immediately in case the execution worker has already finished.
  await checkStatus()
}

async function handleConfirm() {
  if (!pendingRequest.value) return
  confirming.value = true
  errorMessage.value = null

  try {
    await actionsApi.confirmChangeRequest(pendingRequest.value.id)
    stage.value = 'executing'
    await startPolling()
  } catch (err) {
    const apiErr = err as ApiError
    errorMessage.value = apiErr.message || 'Failed to queue execution.'
  } finally {
    confirming.value = false
  }
}

function handleClose() {
  if (submitting.value || confirming.value || stage.value === 'executing') return
  stopPolling()

  // Only announce a real submission — never fires from a plain form-stage cancel.
  const submittedId = pendingRequest.value?.id

  stage.value = 'form'
  selectedActionId.value = ''
  paramValues.value = {}
  errorMessage.value = null
  pendingRequest.value = null
  pollTimedOut.value = false

  if (submittedId) emit('submitted', submittedId)
  emit('close')
}

// Safety net: if the modal's parent unmounts entirely while we're mid-poll
// (e.g. route navigation), don't leave an orphaned interval running.
onUnmounted(stopPolling)
</script>

<template>
  <BaseModal :open="open" title="Execute Safe Network Action" :closeable="!submitting && !confirming && stage !== 'executing'" @close="handleClose">
    <div class="space-y-5">
      <div v-if="device" class="flex items-center justify-between p-3 rounded-lg bg-surface-sunken border border-border">
        <div>
          <span class="text-xs font-semibold uppercase tracking-wider text-text-muted">Target Device</span>
          <h4 class="text-sm font-bold text-text-primary">{{ device.name }}</h4>
        </div>
        <div class="text-right">
          <span class="text-xs font-mono text-text-muted">{{ device.management_ip }}</span>
          <div class="text-xs font-medium text-brand-500 uppercase">{{ device.device_type }}</div>
        </div>
      </div>

      <ErrorAlert v-if="errorMessage" :message="errorMessage" />

      <template v-if="stage === 'form'">
        <div>
          <BaseSelect
            id="action-select"
            v-model="selectedActionId"
            label="Select Network Action"
            :options="actionOptions"
            placeholder="-- Choose a pre-approved template --"
          />
          <p v-if="selectedAction" class="mt-1 text-xs text-text-muted">
            {{ selectedAction.description }}
          </p>
        </div>

        <div v-if="selectedAction" class="p-4 rounded-lg bg-surface-sunken/50 border border-border space-y-4">
          <h5 class="text-xs font-bold uppercase tracking-wider text-text-muted flex items-center gap-1.5">
            <ShieldCheck class="w-4 h-4 text-brand-500" /> Action Parameters
          </h5>

          <div v-for="param in selectedAction.parameters" :key="param.name">
            <label v-if="param.data_type === 'BOOLEAN'" class="flex items-center gap-2 text-sm text-text-primary cursor-pointer">
              <input
                type="checkbox"
                v-model="paramValues[param.name]"
                class="rounded border-border"
              />
              {{ param.label }}
            </label>

            <BaseInput
              v-else-if="param.data_type === 'INTEGER'"
              :id="`param-${param.name}`"
              v-model="paramValues[param.name]"
              :label="param.label"
              type="number"
            />

            <BaseInput
              v-else
              :id="`param-${param.name}`"
              v-model="paramValues[param.name]"
              :label="param.label"
              type="text"
            />
          </div>
        </div>

        <div class="flex items-center justify-end gap-3 pt-3 border-t border-border">
          <BaseButton variant="secondary" @click="handleClose">Cancel</BaseButton>
          <BaseButton
            variant="primary"
            :loading="submitting"
            :disabled="!isFormValid || submitting"
            @click="handleSubmit"
          >
            Generate Commands
          </BaseButton>
        </div>
      </template>

      <template v-else-if="stage === 'review' && pendingRequest">
        <div class="flex items-start gap-2.5 p-3 text-xs rounded-md bg-amber-500/10 text-amber-600 border border-amber-500/20">
          <AlertTriangle class="w-4 h-4 mt-0.5 shrink-0" />
          <span>Nothing has been sent to the device yet. Review the commands below before confirming.</span>
        </div>

        <div>
          <h5 class="text-xs font-bold uppercase tracking-wider text-text-muted mb-2 flex items-center gap-1.5">
            <Terminal class="w-4 h-4 text-brand-500" /> Commands to be sent
          </h5>
          <pre class="text-xs font-mono bg-surface-sunken border border-border rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">{{ pendingRequest.generated_commands }}</pre>
        </div>

        <div class="flex items-center justify-end gap-3 pt-3 border-t border-border">
          <BaseButton variant="secondary" @click="handleClose">Cancel</BaseButton>
          <BaseButton variant="primary" :loading="confirming" @click="handleConfirm">
            Confirm &amp; Execute
          </BaseButton>
        </div>
      </template>

      <template v-else-if="stage === 'executing'">
        <div class="flex flex-col items-center justify-center gap-3 py-10 text-center">
          <Loader2 class="w-8 h-8 text-brand-500 animate-spin" />
          <div>
            <p class="text-sm font-medium text-text-primary">Waiting for the device response…</p>
            <p v-if="!pollTimedOut" class="text-xs text-text-muted mt-1">Waiting for Netmiko, then verifying the running configuration on the device.</p>
            <p v-else class="text-xs text-text-muted mt-1">This is taking longer than usual. Status checks continue every 5 seconds; keep this window open.</p>
          </div>
        </div>
      </template>

      <template v-else-if="stage === 'result' && pendingRequest">
        <div
          v-if="pendingRequest.status === 'PENDING'"
          class="flex items-start gap-2.5 p-4 rounded-lg bg-status-warning-bg text-status-warning border border-status-warning/20"
        >
          <Clock class="w-5 h-5 shrink-0 mt-0.5" />
          <div class="text-sm space-y-1">
            <p class="font-medium">Request saved and waiting for execution.</p>
            <p class="text-xs opacity-90">No final device response has been recorded yet. Find this request in your change activity.</p>
          </div>
        </div>

        <div
          v-else-if="pendingRequest.status === 'SUCCESS'"
          class="flex items-start gap-2.5 p-4 rounded-lg bg-status-success-bg text-status-success border border-status-success/20"
        >
          <CheckCircle class="w-5 h-5 shrink-0 mt-0.5" />
          <div class="text-sm space-y-1">
            <p class="font-medium">Change applied successfully.</p>
            <p v-if="pendingRequest.error_message" class="text-xs opacity-90">{{ pendingRequest.error_message }}</p>
          </div>
        </div>

        <div
          v-else-if="pendingRequest.status === 'FAILED'"
          class="flex items-start gap-2.5 p-4 rounded-lg bg-status-critical-bg text-status-critical border border-status-critical/20"
        >
          <XCircle class="w-5 h-5 shrink-0 mt-0.5" />
          <div class="text-sm space-y-1">
            <p class="font-medium">Execution failed.</p>
            <p v-if="pendingRequest.error_message" class="text-xs opacity-90 font-mono whitespace-pre-wrap">{{ pendingRequest.error_message }}</p>
          </div>
        </div>

        <div
          v-else
          class="flex items-start gap-2.5 p-4 rounded-lg bg-status-warning-bg text-status-warning border border-status-warning/20"
        >
          <Clock class="w-5 h-5 shrink-0 mt-0.5" />
          <div class="text-sm space-y-1">
            <p class="font-medium">Still processing.</p>
            <p class="text-xs opacity-90">This is taking longer than usual. Check the Change Requests log later for the final result.</p>
          </div>
        </div>

        <div class="flex justify-end pt-3 border-t border-border">
          <BaseButton variant="primary" @click="handleClose">Close</BaseButton>
        </div>
      </template>
    </div>
  </BaseModal>
</template>