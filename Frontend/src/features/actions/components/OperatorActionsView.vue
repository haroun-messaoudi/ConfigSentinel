<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/features/auth/stores/auth.store'
import BaseButton from '@/components/common/BaseButton.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import ChangeRequestWizardModal from './ChangeRequestWizardModal.vue'
import { actionsApi } from '../api/actions.api'
import { devicesApi } from '@/features/devices/api/devices.api'
import type { ActionDefinition, DevicePermission } from '../types'
import type { Device } from '@/features/devices/types'
import { Play, Server, Wrench } from 'lucide-vue-next'

const permissions = ref<DevicePermission[]>([])
const definitions = ref<ActionDefinition[]>([])
const devices = ref<Device[]>([])
const auth = useAuthStore()

const loading = ref(true)
const error = ref<string | null>(null)

const isWizardOpen = ref(false)
const selectedDeviceForWizard = ref<Device | null>(null)

async function loadData() {
  loading.value = true
  error.value = null
  try {
    const [permRes, defRes, devRes] = await Promise.all([
      actionsApi.listPermissions({ user: auth.user!.id }),
      actionsApi.listDefinitions(),
      devicesApi.list(),
    ])
    permissions.value = permRes
    definitions.value = defRes
    const assignedDeviceIds = new Set(permRes.map((permission) => permission.device))
    devices.value = devRes.filter((device) => assignedDeviceIds.has(device.id))
  } catch {
    error.value = 'Could not load your available actions.'
  } finally {
    loading.value = false
  }
}

// Group this user's permissions by device — each card shows one device
// and which actions they're allowed to run on it.
const grouped = computed(() => {
  const map = new Map<number, { device: Device; actionIds: Set<number> }>()
  for (const perm of permissions.value) {
    const devId = typeof perm.device === 'number' ? perm.device : (perm.device as any)?.id
    const device = devices.value.find((d) => d.id === devId)
    if (!device) continue
    if (!map.has(devId)) map.set(devId, { device, actionIds: new Set() })
    const actionId = typeof perm.action_definition === 'number' ? perm.action_definition : (perm.action_definition as any)?.id
    map.get(devId)!.actionIds.add(actionId)
  }
  return Array.from(map.values())
})

function actionsForDevice(actionIds: Set<number>): ActionDefinition[] {
  return definitions.value.filter((d) => actionIds.has(d.id))
}

function openWizard(device: Device) {
  selectedDeviceForWizard.value = device
  isWizardOpen.value = true
}

onMounted(loadData)
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-xl font-bold text-text-primary flex items-center gap-2">
        <Wrench class="w-6 h-6 text-brand-500" /> Submit a Configuration Change
      </h1>
      <p class="text-sm text-text-muted mt-1">Choose an assigned device and an authorized configuration action.</p>
    </div>

    <ErrorAlert v-if="error" :message="error" />
    <div v-if="loading" class="text-sm text-text-muted">Loading…</div>

    <div v-else-if="grouped.length === 0" class="p-6 text-center text-sm text-text-muted bg-surface-raised border border-border rounded-lg">
      You don't have any action permissions yet. Ask an admin to grant you access.
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div
        v-for="{ device, actionIds } in grouped"
        :key="device.id"
        class="bg-surface-raised border border-border rounded-lg p-4 space-y-3"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Server class="w-4 h-4 text-brand-500" />
            <RouterLink :to="{ name: 'device-detail', params: { id: device.id } }" class="font-semibold text-text-primary hover:text-brand-600">{{ device.name }}</RouterLink>
          </div>
          <div class="text-right">
            <span class="block text-xs font-mono text-text-muted">{{ device.management_ip }}</span>
            <span class="text-[10px]" :class="device.last_poll_status === 'ERROR' ? 'text-status-critical' : device.last_poll_status === 'OK' ? 'text-status-healthy' : 'text-text-muted'">
              {{ !device.is_active ? 'Paused' : device.last_poll_status === 'ERROR' ? 'Polling error' : device.last_poll_status === 'OK' ? 'Connected' : 'Not yet polled' }}
            </span>
          </div>
        </div>

        <div class="flex flex-wrap gap-1.5">
          <span
            v-for="action in actionsForDevice(actionIds)"
            :key="action.id"
            class="text-xs px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-600"
          >
            {{ action.name }}
          </span>
        </div>

        <BaseButton variant="primary" class="w-full" @click="openWizard(device)">
          <Play class="w-4 h-4 mr-1.5" /> Prepare Change
        </BaseButton>
      </div>
    </div>

    <ChangeRequestWizardModal
      :open="isWizardOpen"
      :device="selectedDeviceForWizard"
      :can-confirm="true"
      :available-actions="selectedDeviceForWizard ? actionsForDevice(grouped.find(g => g.device.id === selectedDeviceForWizard!.id)?.actionIds ?? new Set()) : []"
      @close="isWizardOpen = false"
      @submitted="isWizardOpen = false"
    />
  </div>
</template>