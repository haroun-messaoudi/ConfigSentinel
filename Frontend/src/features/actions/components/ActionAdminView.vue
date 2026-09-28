<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseSelect from '@/components/common/BaseSelect.vue'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import ChangeRequestWizardModal from './ChangeRequestWizardModal.vue'
import { actionsApi, type ChoiceOption } from '../api/actions.api'
import { devicesApi, deviceTypesApi } from '@/features/devices/api/devices.api'
import { usersApi } from '@/features/users/api/users.api'
import type { ActionDefinition, DevicePermission } from '../types'
import type { Device } from '@/features/devices/types'
import type { AppUser } from '@/features/users/types'
import { Shield, Key, Plus, Trash2, CheckCircle2, Play, CheckSquare, Square, Code2, Sliders, Search, X } from 'lucide-vue-next'

const definitions = ref<ActionDefinition[]>([])
const permissions = ref<DevicePermission[]>([])
const devices = ref<Device[]>([])
const users = ref<AppUser[]>([])

const loading = ref(true)
const error = ref<string | null>(null)
const successMsg = ref<string | null>(null)

// Permission Form state
const selectedUser = ref<number | string>('')
const selectedDevice = ref<number | string>('')
const selectedActions = ref<number[]>([])
const assigning = ref(false)
const permissionSearch = ref('')
const permissionUserFilter = ref('ALL')
const permissionDeviceFilter = ref('ALL')
const permissionActionFilter = ref('ALL')

// Create Action Definition Modal state
const isCreateActionOpen = ref(false)
const savingAction = ref(false)

// Single source of truth: device types come from the devices app's own
// /devices/types/ endpoint (SUPPORTED_DEVICE_TYPES), data types come from
// actions/action-choices/ (ActionParameter.DATA_TYPES) — neither is
// hardcoded here, so a backend change updates this form automatically.
const deviceTypeOptions = ref<ChoiceOption[]>([])
const dataTypeOptions = ref<ChoiceOption[]>([])

const form = reactive({
  name: '',
  description: '',
  parameters: [
    { name: '', label: '', data_type: 'STRING' as const, is_required: true }
  ],
  templates: [
    { device_type: '', template_text: '' }
  ]
})

// Wizard Execution Modal state
const isWizardOpen = ref(false)
const selectedDeviceForWizard = ref<Device | null>(null)

const isAllActionsSelected = computed(() => {
  return definitions.value.length > 0 && selectedActions.value.length === definitions.value.length
})

function permissionUserName(permission: DevicePermission) {
  return permission.user_username || users.value.find((user) => user.id === permission.user)?.username || `User #${permission.user}`
}

function permissionDeviceName(permission: DevicePermission) {
  return permission.device_name || devices.value.find((device) => device.id === permission.device)?.name || `Device #${permission.device}`
}

function permissionActionName(permission: DevicePermission) {
  return permission.action_name || definitions.value.find((action) => action.id === permission.action_definition)?.name || `Action #${permission.action_definition}`
}

function permissionGrantor(permission: DevicePermission) {
  if (!permission.granted_by) return 'Unknown / legacy grant'
  return users.value.find((user) => user.id === permission.granted_by)?.username || `User #${permission.granted_by}`
}

const filteredPermissions = computed(() => {
  const query = permissionSearch.value.trim().toLowerCase()
  return permissions.value
    .filter((permission) => permissionUserFilter.value === 'ALL' || String(permission.user) === permissionUserFilter.value)
    .filter((permission) => permissionDeviceFilter.value === 'ALL' || String(permission.device) === permissionDeviceFilter.value)
    .filter((permission) => permissionActionFilter.value === 'ALL' || String(permission.action_definition) === permissionActionFilter.value)
    .filter((permission) => !query || [permissionUserName(permission), permissionDeviceName(permission), permissionActionName(permission), permissionGrantor(permission)].some((value) => value.toLowerCase().includes(query)))
    .sort((a, b) => permissionUserName(a).localeCompare(permissionUserName(b)) || permissionDeviceName(a).localeCompare(permissionDeviceName(b)) || permissionActionName(a).localeCompare(permissionActionName(b)))
})

const assignmentUserOptions = computed(() => Array.from(new Map(permissions.value.map((permission) => [permission.user, permissionUserName(permission)])).entries()).sort((a, b) => a[1].localeCompare(b[1])))
const assignmentDeviceOptions = computed(() => Array.from(new Map(permissions.value.map((permission) => [permission.device, permissionDeviceName(permission)])).entries()).sort((a, b) => a[1].localeCompare(b[1])))
const assignmentActionOptions = computed(() => Array.from(new Map(permissions.value.map((permission) => [permission.action_definition, permissionActionName(permission)])).entries()).sort((a, b) => a[1].localeCompare(b[1])))

async function loadData() {
  loading.value = true
  error.value = null

  try {
    const [defRes, permRes, devRes, userRes, deviceTypesRes, actionChoicesRes] = await Promise.all([
      actionsApi.listDefinitions().catch((err) => { console.error('listDefinitions failed:', err); return [] }),
      actionsApi.listPermissions().catch((err) => { console.error('listPermissions failed:', err); return [] }),
      devicesApi.list().catch((err) => { console.error('devicesApi failed:', err); return [] }),
      usersApi.list().catch((err) => { console.error('usersApi failed:', err); return [] }),
      deviceTypesApi.list().catch((err) => { console.error('deviceTypesApi failed:', err); return [] }),
      actionsApi.getChoices().catch((err) => { console.error('getChoices failed:', err); return null }),
    ])

    definitions.value = defRes
    permissions.value = permRes
    devices.value = devRes
    users.value = userRes

    if (deviceTypesRes.length) deviceTypeOptions.value = deviceTypesRes
    if (actionChoicesRes?.data_types?.length) dataTypeOptions.value = actionChoicesRes.data_types

    if (deviceTypeOptions.value.length && !form.templates[0].device_type) {
      form.templates[0].device_type = deviceTypeOptions.value[0].value
    }
    if (dataTypeOptions.value.length) {
      form.parameters[0].data_type = dataTypeOptions.value[0].value as any
    }
  } catch (err: any) {
    error.value = 'Failed to load configuration governance data.'
  } finally {
    loading.value = false
  }
}

function toggleActionSelection(actionId: number) {
  const index = selectedActions.value.indexOf(actionId)
  if (index === -1) {
    selectedActions.value.push(actionId)
  } else {
    selectedActions.value.splice(index, 1)
  }
}

function toggleSelectAllActions() {
  if (isAllActionsSelected.value) {
    selectedActions.value = []
  } else {
    selectedActions.value = definitions.value.map((d) => d.id)
  }
}

async function handleAssignPermission() {
  if (!selectedUser.value || !selectedDevice.value || selectedActions.value.length === 0) return
  assigning.value = true
  error.value = null
  successMsg.value = null

  try {
    await Promise.all(
      selectedActions.value.map((actionId) =>
        actionsApi.assignPermission({
          user: Number(selectedUser.value),
          device: Number(selectedDevice.value),
          action_definition: actionId,
        })
      )
    )

    successMsg.value = `Successfully granted ${selectedActions.value.length} action permission(s)!`
    selectedUser.value = ''
    selectedDevice.value = ''
    selectedActions.value = []
    await loadData()
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to assign one or more permissions.'
  } finally {
    assigning.value = false
  }
}

async function handleRevoke(permissionId: number) {
  try {
    await actionsApi.revokePermission(permissionId)
    await loadData()
  } catch (err: any) {
    error.value = 'Failed to revoke permission.'
  }
}

function addParamField() {
  const defaultType = dataTypeOptions.value[0]?.value || 'STRING'
  form.parameters.push({ name: '', label: '', data_type: defaultType as any, is_required: true })
}

function removeParamField(index: number) {
  form.parameters.splice(index, 1)
}

function addTemplateField() {
  const defaultDevType = deviceTypeOptions.value[0]?.value || ''
  form.templates.push({ device_type: defaultDevType, template_text: '' })
}

function removeTemplateField(index: number) {
  form.templates.splice(index, 1)
}

function resetForm() {
  form.name = ''
  form.description = ''
  form.parameters = [{ name: '', label: '', data_type: (dataTypeOptions.value[0]?.value || 'STRING') as any, is_required: true }]
  form.templates = [{ device_type: deviceTypeOptions.value[0]?.value || '', template_text: '' }]
}

async function handleCreateActionDefinition() {
  if (!form.name.trim()) {
    error.value = 'Action name is required.'
    return
  }

  const validTemplates = form.templates.filter(t => t.device_type && t.template_text.trim())
  if (validTemplates.length === 0) {
    error.value = 'At least one CLI command template text is required.'
    return
  }

  savingAction.value = true
  error.value = null

  try {
    const validParams = form.parameters.filter((p) => p.name.trim() !== '' && p.label.trim() !== '')

    await actionsApi.createDefinition({
      name: form.name.trim(),
      description: form.description.trim(),
      parameters: validParams,
      templates: validTemplates
    })

    isCreateActionOpen.value = false
    resetForm()
    successMsg.value = 'New action template created successfully!'
    await loadData()
  } catch (err: any) {
    const errData = err.response?.data
    if (typeof errData === 'object' && errData !== null) {
      error.value = Object.entries(errData)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        .join(' | ')
    } else {
      error.value = errData?.detail || 'Failed to create action definition template.'
    }
  } finally {
    savingAction.value = false
  }
}

function openExecutionWizard(perm: any) {
  const devId = typeof perm.device === 'number' ? perm.device : (perm.device?.id || perm.device_id)
  const foundDev = devices.value.find((d) => d.id === devId)
  if (foundDev) {
    selectedDeviceForWizard.value = foundDev
    isWizardOpen.value = true
  }
}

onMounted(loadData)
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold text-text-primary flex items-center gap-2">
          <Shield class="w-6 h-6 text-brand-500" /> Action & Governance Matrix
        </h1>
        <p class="text-sm text-text-muted mt-1">
          Manage safe network action templates and assign granular execution rights to technicians.
        </p>
      </div>

      <BaseButton variant="primary" @click="isCreateActionOpen = true">
        <Plus class="w-4 h-4 mr-1.5" /> New Action Template
      </BaseButton>
    </div>

    <ErrorAlert v-if="error" :message="error" />
    <div
      v-if="successMsg"
      class="p-3 rounded-md bg-status-success-bg text-status-success text-sm flex items-center gap-2 border border-status-success/20"
    >
      <CheckCircle2 class="w-4 h-4" /> {{ successMsg }}
    </div>

    <!-- Main Grid: Assign Rights & Active Matrix -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Left Panel: Batch Assign Permissions -->
      <div class="bg-surface-raised border border-border rounded-lg p-5 space-y-4">
        <h3 class="text-base font-semibold text-text-primary flex items-center gap-2">
          <Key class="w-4 h-4 text-brand-500" /> Grant Execution Rights
        </h3>

        <div>
          <BaseSelect
            id="user-select"
            v-model="selectedUser"
            label="User / Technician"
            :options="users.map((u) => ({ value: u.id, label: u.username }))"
            placeholder="-- Select User --"
          />
        </div>

        <div>
          <BaseSelect
            id="device-select"
            v-model="selectedDevice"
            label="Target Device"
            :options="devices.map((d) => ({ value: d.id, label: `${d.name} (${d.management_ip})` }))"
            placeholder="-- Select Device --"
          />
        </div>

        <!-- Multi-Action Selection List -->
        <div>
          <div class="flex items-center justify-between mb-2">
            <label class="block text-xs font-semibold text-text-muted uppercase">Allowed Actions</label>
            <button
              v-if="definitions.length > 0"
              type="button"
              class="text-xs text-brand-500 hover:underline font-medium"
              @click="toggleSelectAllActions"
            >
              {{ isAllActionsSelected ? 'Deselect All' : 'Select All' }}
            </button>
          </div>

          <div class="max-h-48 overflow-y-auto space-y-1.5 p-2 rounded-md bg-surface-sunken border border-border">
            <div
              v-for="def in definitions"
              :key="def.id"
              class="flex items-center gap-2.5 p-1.5 rounded hover:bg-surface-raised cursor-pointer transition-colors"
              @click="toggleActionSelection(def.id)"
            >
              <component
                :is="selectedActions.includes(def.id) ? CheckSquare : Square"
                class="w-4 h-4 text-brand-500 shrink-0"
              />
              <span class="text-sm text-text-primary font-medium select-none">{{ def.name }}</span>
            </div>

            <div v-if="definitions.length === 0" class="text-xs text-text-muted p-2 text-center">
              No action templates available.
            </div>
          </div>
        </div>

        <BaseButton
          variant="primary"
          class="w-full mt-2"
          :loading="assigning"
          :disabled="!selectedUser || !selectedDevice || selectedActions.length === 0 || assigning"
          @click="handleAssignPermission"
        >
          <Plus class="w-4 h-4 mr-1" />
          Grant {{ selectedActions.length > 0 ? `${selectedActions.length} Action(s)` : 'Permissions' }}
        </BaseButton>
      </div>

      <!-- Right Panel: Active Permission Table -->
      <div class="lg:col-span-2 bg-surface-raised border border-border rounded-lg p-5">
        <div class="mb-4 flex items-start justify-between gap-3">
          <div>
            <h3 class="text-base font-semibold text-text-primary">Permission assignments</h3>
            <p class="mt-0.5 text-xs text-text-secondary">{{ permissions.length }} grants · one row per user, device, and action</p>
          </div>
          <span class="rounded bg-surface-sunken px-2 py-1 text-[10px] font-semibold uppercase text-text-secondary">Access register</span>
        </div>

        <div class="mb-4 grid grid-cols-1 gap-2 sm:grid-cols-2 2xl:grid-cols-4">
          <label class="relative block">
            <Search class="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-muted" />
            <input v-model="permissionSearch" type="search" placeholder="Search assignments" class="w-full rounded-md border border-border bg-surface-raised py-2 pl-8 pr-8 text-xs text-text-primary placeholder:text-text-muted focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20" />
            <button v-if="permissionSearch" type="button" title="Clear search" class="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary" @click="permissionSearch = ''"><X class="h-3.5 w-3.5" /></button>
          </label>
          <select v-model="permissionUserFilter" aria-label="Filter by user" class="rounded-md border border-border bg-surface-raised px-2.5 py-2 text-xs text-text-primary">
            <option value="ALL">All users</option>
            <option v-for="[id, name] in assignmentUserOptions" :key="id" :value="String(id)">{{ name }}</option>
          </select>
          <select v-model="permissionDeviceFilter" aria-label="Filter by device" class="rounded-md border border-border bg-surface-raised px-2.5 py-2 text-xs text-text-primary">
            <option value="ALL">All devices</option>
            <option v-for="[id, name] in assignmentDeviceOptions" :key="id" :value="String(id)">{{ name }}</option>
          </select>
          <select v-model="permissionActionFilter" aria-label="Filter by action" class="rounded-md border border-border bg-surface-raised px-2.5 py-2 text-xs text-text-primary">
            <option value="ALL">All actions</option>
            <option v-for="[id, name] in assignmentActionOptions" :key="id" :value="String(id)">{{ name }}</option>
          </select>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full min-w-[760px] text-left text-sm">
            <thead>
              <tr class="border-b border-border text-xs uppercase text-text-muted">
                <th class="pb-3 pr-3 font-semibold">Assigned user</th>
                <th class="pb-3 pr-3 font-semibold">Device</th>
                <th class="pb-3 pr-3 font-semibold">Allowed action</th>
                <th class="pb-3 pr-3 font-semibold">Granted by</th>
                <th class="pb-3 pr-3 font-semibold">Granted at</th>
                <th class="pb-3 font-semibold text-right">Manage</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border">
              <tr v-for="perm in filteredPermissions" :key="perm.id" class="hover:bg-surface-sunken/50">
                <td class="py-3 pr-3 font-medium text-text-primary">
                  {{ permissionUserName(perm) }}
                </td>
                <td class="py-3 pr-3 text-text-primary">
                  {{ permissionDeviceName(perm) }}
                </td>
                <td class="py-3 pr-3 font-medium text-brand-600">
                  {{ permissionActionName(perm) }}
                </td>
                <td class="py-3 pr-3 text-xs text-text-secondary">{{ permissionGrantor(perm) }}</td>
                <td class="py-3 pr-3 text-xs text-text-secondary">{{ perm.granted_at ? new Date(perm.granted_at).toLocaleString() : '—' }}</td>
                <td class="py-3 text-right">
                  <div class="flex items-center justify-end gap-2">
                  <button
                    class="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-semibold text-brand-600 hover:bg-brand-500/10"
                    title="Preview an action using this permission"
                    @click="openExecutionWizard(perm)"
                  >
                    <Play class="w-3.5 h-3.5" /> Run
                  </button>
                  <button
                    class="rounded p-1.5 text-text-muted hover:bg-status-critical-bg hover:text-status-critical"
                    title="Revoke permission"
                    :aria-label="`Revoke ${permissionActionName(perm)} for ${permissionUserName(perm)} on ${permissionDeviceName(perm)}`"
                    @click="handleRevoke(perm.id)"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                  </div>
                </td>
              </tr>
              <tr v-if="filteredPermissions.length === 0">
                <td colspan="6" class="py-8 text-center text-sm text-text-muted">
                  {{ permissions.length ? 'No assignments match these filters.' : 'No explicit permissions granted yet.' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Modal 1: Create New Action Template Definition with Nested Parameters and CLI Templates -->
    <BaseModal :open="isCreateActionOpen" title="Create Action Template" @close="isCreateActionOpen = false">
      <div class="space-y-6 max-h-[80vh] overflow-y-auto pr-1">
        <!-- Basic Info -->
        <div class="space-y-3">
          <BaseInput id="act-name" v-model="form.name" label="Action Name" placeholder="e.g. Configure Extended ACL" />
          <BaseInput id="act-desc" v-model="form.description" label="Description" placeholder="Short summary of what this action does..." />
        </div>

        <!-- Form Parameter Inputs Section -->
        <div class="p-4 rounded-lg bg-surface-sunken/50 border border-border space-y-3">
          <div class="flex items-center justify-between">
            <label class="block text-xs font-bold text-text-muted uppercase flex items-center gap-1.5">
              <Sliders class="w-4 h-4 text-brand-500" /> Form Parameters
            </label>
            <button class="text-xs text-brand-500 hover:underline font-semibold flex items-center gap-1" @click="addParamField">
              <Plus class="w-3.5 h-3.5" /> Add Parameter
            </button>
          </div>

          <div v-for="(p, idx) in form.parameters" :key="idx" class="grid grid-cols-12 gap-2 items-center p-2 rounded bg-surface border border-border">
            <div class="col-span-4">
              <BaseInput :id="`p-name-${idx}`" v-model="p.name" placeholder="Key (e.g. acl_name)" />
            </div>
            <div class="col-span-4">
              <BaseInput :id="`p-label-${idx}`" v-model="p.label" placeholder="Label (e.g. ACL Name)" />
            </div>
            <div class="col-span-3">
              <BaseSelect :id="`p-type-${idx}`" v-model="p.data_type" :options="dataTypeOptions" />
            </div>
            <div class="col-span-1 flex justify-center">
              <button
                type="button"
                class="p-1 text-text-muted hover:text-status-critical transition-colors"
                @click="removeParamField(idx)"
                :disabled="form.parameters.length === 1"
              >
                <Trash2 class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        <!-- Jinja2 CLI Templates Section -->
        <div class="p-4 rounded-lg bg-surface-sunken/50 border border-border space-y-3">
          <div class="flex items-center justify-between">
            <label class="block text-xs font-bold text-text-muted uppercase flex items-center gap-1.5">
              <Code2 class="w-4 h-4 text-brand-500" /> CLI Command Templates (Jinja2)
            </label>
            <button class="text-xs text-brand-500 hover:underline font-semibold flex items-center gap-1" @click="addTemplateField">
              <Plus class="w-3.5 h-3.5" /> Add Device Target
            </button>
          </div>

          <div v-for="(tmpl, idx) in form.templates" :key="idx" class="space-y-2 p-3 rounded bg-surface border border-border">
            <div class="flex items-center justify-between">
              <div class="w-1/2">
                <BaseSelect
                  :id="`tmpl-device-${idx}`"
                  v-model="tmpl.device_type"
                  label="Target Device Driver"
                  :options="deviceTypeOptions"
                />
              </div>
              <button
                type="button"
                class="p-1 text-text-muted hover:text-status-critical transition-colors mt-4"
                @click="removeTemplateField(idx)"
                :disabled="form.templates.length === 1"
              >
                <Trash2 class="w-4 h-4" />
              </button>
            </div>

            <div>
              <label :for="`tmpl-text-${idx}`" class="block text-xs font-medium text-text-secondary mb-1">
                Jinja2 CLI Template Text
              </label>
              <textarea
                :id="`tmpl-text-${idx}`"
                v-model="tmpl.template_text"
                rows="3"
                class="w-full text-xs font-mono bg-surface-sunken border border-border rounded-lg p-2.5 focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 outline-none text-text-primary"
                placeholder="ip access-list extended {{ acl_name }}"
              ></textarea>
            </div>
          </div>
        </div>

        <!-- Modal Actions -->
        <div class="flex justify-end gap-3 pt-3 border-t border-border">
          <BaseButton variant="secondary" @click="isCreateActionOpen = false">Cancel</BaseButton>
          <BaseButton variant="primary" :loading="savingAction" @click="handleCreateActionDefinition">Save Template</BaseButton>
        </div>
      </div>
    </BaseModal>

    <!-- Modal 2: Execution Wizard Trigger -->
    <ChangeRequestWizardModal
      :open="isWizardOpen"
      :device="selectedDeviceForWizard"
      :available-actions="definitions"
      :can-confirm="true"
      @close="isWizardOpen = false"
      @submitted="isWizardOpen = false"
    />
  </div>
</template>