<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/features/auth/stores/auth.store'
import { devicesApi } from '../api/devices.api'
import { changesApi } from '@/features/changes/api/changes.api'
import { snapshotsApi } from '@/features/snapshots/api/snapshots.api'
import { useCheckNow } from '../composables/useCheckNow'
import type { Device } from '../types'
import type { ConfigChange, ChangeStatus } from '@/features/changes/types'
import type { Snapshot } from '@/features/snapshots/types'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import DeviceFormModal from './DeviceFormModal.vue'
import {
  RefreshCw,
  Pause,
  Play,
  Pencil,
  Trash2,
  History,
  GitCompareArrows,
  ShieldAlert,
  CheckCircle2,
  Info,
  Star,
} from 'lucide-vue-next'

const props = defineProps<{ id: string }>()
const router = useRouter()
const auth = useAuthStore()
const { checkingIds, checkErrors, checkNow } = useCheckNow()

const device = ref<Device | null>(null)
const isLoading = ref(true)
const loadError = ref<string | null>(null)
const actionError = ref<string | null>(null)
const isActing = ref(false)
const showEditModal = ref(false)
const showDeleteConfirm = ref(false)
const isDeleting = ref(false)
const deleteError = ref<string | null>(null)

const recentChanges = ref<ConfigChange[]>([])
const changesLoading = ref(true)
const changesError = ref<string | null>(null)

const recentSnapshots = ref<Snapshot[]>([])
const snapshotsLoading = ref(true)
const snapshotsError = ref<string | null>(null)

const statusBadge = computed(() => {
  if (!device.value) return { text: '', class: '' }
  if (!device.value.is_active) return { text: 'Paused', class: 'bg-status-neutral-bg text-status-neutral' }
  if (device.value.last_poll_status === 'OK') return { text: 'Healthy', class: 'bg-status-healthy-bg text-status-healthy' }
  if (device.value.last_poll_status === 'ERROR') return { text: 'Failing', class: 'bg-status-critical-bg text-status-critical' }
  return { text: 'Never polled', class: 'bg-status-neutral-bg text-status-neutral' }
})

async function loadDevice() {
  isLoading.value = true
  loadError.value = null
  try {
    device.value = await devicesApi.get(props.id)
  } catch {
    loadError.value = 'Could not load this device.'
  } finally {
    isLoading.value = false
  }
}

async function loadRecentChanges() {
  changesLoading.value = true
  changesError.value = null
  try {
    recentChanges.value = (await changesApi.list({ device: props.id })).slice(0, 5)
  } catch {
    changesError.value = 'Could not load recent config changes.'
  } finally {
    changesLoading.value = false
  }
}

async function loadRecentSnapshots() {
  snapshotsLoading.value = true
  snapshotsError.value = null
  try {
    recentSnapshots.value = (await snapshotsApi.listForDevice(props.id)).slice(0, 5)
  } catch {
    snapshotsError.value = 'Could not load recent snapshots.'
  } finally {
    snapshotsLoading.value = false
  }
}

onMounted(() => {
  loadDevice()
  loadRecentChanges()
  loadRecentSnapshots()
})

async function runAction(action: 'pause' | 'resume') {
  if (!device.value) return
  actionError.value = null
  isActing.value = true
  try {
    if (action === 'pause') {
      device.value = (await devicesApi.pause(device.value.id)).data
    } else {
      device.value = (await devicesApi.resume(device.value.id)).data
    }
  } catch {
    actionError.value = 'Action failed. Please try again.'
  } finally {
    isActing.value = false
  }
}

function onSaved(updated: Device) {
  device.value = updated
}

async function confirmDelete() {
  if (!device.value) return
  isDeleting.value = true
  deleteError.value = null
  try {
    await devicesApi.remove(device.value.id)
    router.push({ name: 'devices' })
  } catch {
    deleteError.value = 'Could not delete this device.'
    isDeleting.value = false
  }
}

function severityClass(name: string | null) {
  const s = name?.toLowerCase()
  if (s === 'high' || s === 'critical') return 'bg-status-critical-bg text-status-critical'
  if (s === 'medium') return 'bg-status-warning-bg text-status-warning'
  if (s === 'low') return 'bg-status-neutral-bg text-status-neutral'
  return 'bg-status-neutral-bg text-status-neutral'
}

function statusMeta(status: ChangeStatus) {
  if (status === 'ACKNOWLEDGED') return { class: 'bg-status-healthy-bg text-status-healthy', icon: CheckCircle2 }
  if (status === 'FLAGGED') return { class: 'bg-status-critical-bg text-status-critical', icon: ShieldAlert }
  return { class: 'bg-status-neutral-bg text-status-neutral', icon: Info }
}
</script>

<template>
  <div>
    <button type="button" class="mb-4 text-sm text-text-secondary hover:text-text-primary" @click="router.push({ name: 'devices' })">
      ← Back to Devices
    </button>

    <ErrorAlert v-if="loadError" :message="loadError" class="mb-4" />

    <div v-if="isLoading" class="text-sm text-text-secondary">Loading…</div>

    <template v-else-if="device">
      <div class="bg-surface-raised border border-border rounded-lg shadow-sm p-6">
        <div class="flex items-start justify-between mb-4">
          <div>
            <h2 class="text-xl font-semibold text-text-primary">{{ device.name }}</h2>
            <p class="text-sm text-text-secondary">{{ device.hostname }} · {{ device.management_ip }}:{{ device.port }}</p>
          </div>
          <span class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium" :class="statusBadge.class">
            {{ statusBadge.text }}
          </span>
        </div>

        <dl class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-6">
          <div>
            <dt class="text-text-secondary">Device Type</dt>
            <dd class="text-text-primary">{{ device.device_type }}</dd>
          </div>
          <div>
            <dt class="text-text-secondary">Poll Interval</dt>
            <dd class="text-text-primary">{{ device.poll_interval_minutes }} min</dd>
          </div>
          <div>
            <dt class="text-text-secondary">Last Polled</dt>
            <dd class="text-text-primary">
              {{ device.last_polled_at ? new Date(device.last_polled_at).toLocaleString() : 'Never' }}
            </dd>
          </div>
          <div>
            <dt class="text-text-secondary">Consecutive Failures</dt>
            <dd class="text-text-primary">{{ device.consecutive_failures }}</dd>
          </div>
          <div v-if="device.last_poll_error" class="col-span-2 md:col-span-4">
            <dt class="text-text-secondary">Last Error</dt>
            <dd class="text-status-critical font-mono text-xs mt-1">{{ device.last_poll_error }}</dd>
          </div>
        </dl>

        <ErrorAlert v-if="actionError" :message="actionError" class="mb-4" />
        <p v-if="checkErrors[device.id]" class="text-xs text-status-warning mb-4">{{ checkErrors[device.id] }}</p>

        <div class="flex flex-wrap gap-2">
          <BaseButton
            v-if="auth.hasRole('admin', 'operator')"
            variant="secondary"
            :disabled="checkingIds.has(device.id)"
            @click="checkNow(device, (updated) => (device = updated))"
          >
            <RefreshCw class="w-4 h-4" :class="{ 'animate-spin': checkingIds.has(device.id) }" />
            {{ checkingIds.has(device.id) ? 'Checking…' : 'Check Now' }}
          </BaseButton>
          <BaseButton
            v-if="auth.hasRole('admin', 'operator')"
            variant="secondary"
            :disabled="isActing"
            @click="runAction(device.is_active ? 'pause' : 'resume')"
          >
            <component :is="device.is_active ? Pause : Play" class="w-4 h-4" />
            {{ device.is_active ? 'Pause' : 'Resume' }}
          </BaseButton>
          <BaseButton variant="secondary" @click="router.push({ name: 'device-snapshots', params: { id: device.id } })">
            <History class="w-4 h-4" />
            View Snapshots
          </BaseButton>
          <BaseButton v-if="auth.hasRole('admin', 'operator')" @click="showEditModal = true">
            <Pencil class="w-4 h-4" />
            Edit
          </BaseButton>
          <BaseButton v-if="auth.hasRole('admin')" variant="danger" @click="showDeleteConfirm = true">
            <Trash2 class="w-4 h-4" />
            Delete
          </BaseButton>
        </div>
      </div>

      <div v-if="showDeleteConfirm" class="mt-4 bg-surface-raised border border-status-critical/30 rounded-lg p-4">
        <p class="text-sm text-text-primary mb-3">
          Delete <strong>{{ device.name }}</strong>? This cannot be undone.
        </p>
        <ErrorAlert v-if="deleteError" :message="deleteError" class="mb-3" />
        <div class="flex gap-2">
          <BaseButton variant="danger" :loading="isDeleting" @click="confirmDelete">
            {{ isDeleting ? 'Deleting…' : 'Confirm Delete' }}
          </BaseButton>
          <BaseButton variant="secondary" :disabled="isDeleting" @click="showDeleteConfirm = false">Cancel</BaseButton>
        </div>
      </div>

      <!-- Recent activity: config changes + snapshots for this device -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <div class="bg-surface-raised border border-border rounded-lg shadow-sm p-5">
          <div class="flex items-center gap-2 mb-4">
            <GitCompareArrows class="w-4 h-4 text-text-secondary" />
            <h3 class="text-sm font-semibold text-text-primary">Recent Config Changes</h3>
          </div>

          <ErrorAlert v-if="changesError" :message="changesError" class="mb-3" />
          <div v-if="changesLoading" class="space-y-2">
            <div v-for="i in 3" :key="i" class="h-10 rounded-lg bg-surface-sunken animate-pulse" />
          </div>
          <div v-else-if="recentChanges.length === 0" class="text-center py-6 text-xs text-text-muted">
            No config changes detected for this device yet.
          </div>
          <div v-else class="divide-y divide-border">
            <RouterLink
              v-for="change in recentChanges"
              :key="change.id"
              :to="{ name: 'change-detail', params: { id: change.id } }"
              class="py-2.5 flex items-center justify-between gap-3 hover:opacity-80"
            >
              <div class="min-w-0">
                <p class="text-xs font-medium text-text-primary truncate">
                  {{ change.matched_concept_names.length ? change.matched_concept_names.join(', ') : 'General drift' }}
                </p>
                <p class="text-xs text-text-secondary">{{ new Date(change.detected_at).toLocaleString() }}</p>
              </div>
              <div class="flex items-center gap-1.5 shrink-0">
                <span v-if="change.severity_name" class="px-2 py-0.5 rounded-full text-[10px] font-medium" :class="severityClass(change.severity_name)">
                  {{ change.severity_name }}
                </span>
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium" :class="statusMeta(change.status).class">
                  <component :is="statusMeta(change.status).icon" class="w-3 h-3" />
                </span>
              </div>
            </RouterLink>
          </div>
        </div>

        <div class="bg-surface-raised border border-border rounded-lg shadow-sm p-5">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <History class="w-4 h-4 text-text-secondary" />
              <h3 class="text-sm font-semibold text-text-primary">Recent Snapshots</h3>
            </div>
            <RouterLink
              :to="{ name: 'device-snapshots', params: { id: device.id } }"
              class="text-xs font-semibold text-brand-600 hover:text-brand-700"
            >
              View all
            </RouterLink>
          </div>

          <ErrorAlert v-if="snapshotsError" :message="snapshotsError" class="mb-3" />
          <div v-if="snapshotsLoading" class="space-y-2">
            <div v-for="i in 3" :key="i" class="h-10 rounded-lg bg-surface-sunken animate-pulse" />
          </div>
          <div v-else-if="recentSnapshots.length === 0" class="text-center py-6 text-xs text-text-muted">
            No snapshots recorded for this device yet.
          </div>
          <div v-else class="divide-y divide-border">
            <RouterLink
              v-for="snapshot in recentSnapshots"
              :key="snapshot.id"
              :to="{ name: 'device-snapshots', params: { id: device.id } }"
              class="py-2.5 flex items-center justify-between gap-3 hover:opacity-80"
            >
              <div class="min-w-0">
                <p class="text-xs font-medium text-text-primary">{{ new Date(snapshot.taken_at).toLocaleString() }}</p>
                <p class="text-xs text-text-secondary font-mono">{{ snapshot.config_hash.slice(0, 12) }}</p>
              </div>
              <span
                v-if="snapshot.is_baseline"
                class="inline-flex items-center gap-1 shrink-0 px-2 py-0.5 rounded-full text-[10px] font-medium bg-status-healthy-bg text-status-healthy"
              >
                <Star class="w-3 h-3" />
                Baseline
              </span>
            </RouterLink>
          </div>
        </div>
      </div>
    </template>

    <DeviceFormModal v-if="device" :open="showEditModal" mode="edit" :device="device" @close="showEditModal = false" @saved="onSaved" />
  </div>
</template>