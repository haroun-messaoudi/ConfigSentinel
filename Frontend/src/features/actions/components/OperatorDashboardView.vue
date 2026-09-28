<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { actionsApi } from '@/features/actions/api/actions.api'
import type { ChangeRequestItem } from '@/features/actions/types'
import { devicesApi } from '@/features/devices/api/devices.api'
import type { Device } from '@/features/devices/types'
import { listChangesForDevices, getOperatorDeviceIds } from '@/utils/operatorScope'
import type { ConfigChange } from '@/features/changes/types'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { Activity, ArrowRight, Check, CircleAlert, Clock3, GitCompareArrows, Play, Server, Wrench } from 'lucide-vue-next'

const loading = ref(true)
const error = ref<string | null>(null)
const devices = ref<Device[]>([])
const requests = ref<ChangeRequestItem[]>([])
const changes = ref<ConfigChange[]>([])

async function loadWorkspace() {
  loading.value = true
  error.value = null
  try {
    const deviceIds = await getOperatorDeviceIds()
    const [allDevices, allRequests, scopedChanges] = await Promise.all([
      devicesApi.list(),
      actionsApi.listChangeRequests(),
      listChangesForDevices(deviceIds),
    ])
    devices.value = allDevices.filter((device) => deviceIds.has(device.id))
    requests.value = allRequests
      .filter((request) => deviceIds.has(request.device))
      .sort((a, b) => new Date(b.requested_at).getTime() - new Date(a.requested_at).getTime())
    changes.value = scopedChanges
  } catch {
    error.value = 'Could not load your device configuration activity.'
  } finally {
    loading.value = false
  }
}

onMounted(loadWorkspace)

const successfulRequests = computed(() => requests.value.filter((request) => request.status === 'SUCCESS'))
const pendingRequests = computed(() => requests.value.filter((request) => request.status === 'PENDING'))
const failedRequests = computed(() => requests.value.filter((request) => request.status === 'FAILED'))
const flaggedChanges = computed(() => changes.value.filter((change) => change.status === 'FLAGGED'))
const recentRequests = computed(() => requests.value.slice(0, 5))
const recentChanges = computed(() => changes.value.slice(0, 6))

const deviceRows = computed(() => devices.value.map((device) => {
  const deviceRequests = requests.value.filter((request) => request.device === device.id)
  const successful = deviceRequests.filter((request) => request.status === 'SUCCESS')
  const latestSuccess = successful[0]
  return {
    device,
    successCount: successful.length,
    flaggedCount: changes.value.filter((change) => change.device === device.id && change.status === 'FLAGGED').length,
    latestSuccessAt: latestSuccess?.applied_at ?? latestSuccess?.requested_at ?? null,
  }
}))

function deviceHealth(device: Device) {
  if (!device.is_active) return { label: 'Paused', class: 'bg-status-neutral-bg text-status-neutral' }
  if (device.last_poll_status === 'ERROR') return { label: 'Poll error', class: 'bg-status-critical-bg text-status-critical' }
  if (device.last_poll_status === 'OK') return { label: 'Healthy', class: 'bg-status-healthy-bg text-status-healthy' }
  return { label: 'Awaiting first poll', class: 'bg-status-warning-bg text-status-warning' }
}

function formatDate(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString() : 'No successful execution yet'
}
</script>

<template>
  <div class="space-y-8">
    <header class="flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-xs font-semibold uppercase text-brand-600">Operator workspace</p>
        <h1 class="mt-1 text-2xl font-semibold text-text-primary">Configuration overview</h1>
        <p class="mt-1 text-sm text-text-secondary">Your device health, execution history, and detected configuration drift.</p>
      </div>
      <div class="flex gap-2">
        <RouterLink
          :to="{ name: 'my-activity' }"
          class="inline-flex items-center gap-2 rounded-md border border-border bg-surface-raised px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-sunken"
        >
          <Activity class="h-4 w-4" /> My activity
        </RouterLink>
        <RouterLink
          :to="{ name: 'my-actions' }"
          class="inline-flex items-center gap-2 rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          <Play class="h-4 w-4" /> Submit change
        </RouterLink>
      </div>
    </header>

    <ErrorAlert v-if="error" :message="error" />

    <section aria-label="Operator configuration metrics" class="grid grid-cols-2 gap-3 xl:grid-cols-4">
      <div class="border-l-2 border-brand-500 bg-surface-raised px-4 py-3">
        <p class="text-xs font-medium text-text-secondary">Devices in scope</p>
        <p class="mt-1 text-2xl font-semibold tabular-nums text-text-primary">{{ loading ? '—' : devices.length }}</p>
      </div>
      <div class="border-l-2 border-status-healthy bg-surface-raised px-4 py-3">
        <p class="text-xs font-medium text-text-secondary">Successful changes by you</p>
        <p class="mt-1 text-2xl font-semibold tabular-nums text-status-healthy">{{ loading ? '—' : successfulRequests.length }}</p>
      </div>
      <div class="border-l-2 border-status-warning bg-surface-raised px-4 py-3">
        <p class="text-xs font-medium text-text-secondary">Pending execution</p>
        <p class="mt-1 text-2xl font-semibold tabular-nums text-status-warning">{{ loading ? '—' : pendingRequests.length }}</p>
      </div>
      <div class="border-l-2 border-status-critical bg-surface-raised px-4 py-3">
        <p class="text-xs font-medium text-text-secondary">Flagged drift</p>
        <p class="mt-1 text-2xl font-semibold tabular-nums text-status-critical">{{ loading ? '—' : flaggedChanges.length }}</p>
      </div>
    </section>

    <section>
      <div class="mb-3 flex items-end justify-between gap-4">
        <div>
          <h2 class="text-base font-semibold text-text-primary">Devices you control</h2>
          <p class="mt-0.5 text-xs text-text-secondary">Successful execution totals are attributed to your requests.</p>
        </div>
        <RouterLink :to="{ name: 'devices' }" class="shrink-0 text-xs font-medium text-brand-600 hover:text-brand-700">
          Device list <ArrowRight class="inline h-3.5 w-3.5" />
        </RouterLink>
      </div>

      <div v-if="loading" class="h-24 animate-pulse bg-surface-sunken" />
      <div v-else-if="deviceRows.length === 0" class="border-y border-border py-8 text-center text-sm text-text-secondary">
        No devices are assigned to your account yet.
      </div>
      <div v-else class="overflow-x-auto border-y border-border">
        <table class="w-full min-w-[700px] text-left text-sm">
          <thead class="border-b border-border bg-surface-sunken text-[11px] font-semibold uppercase text-text-secondary">
            <tr>
              <th class="px-3 py-2.5">Device</th>
              <th class="px-3 py-2.5">Polling</th>
              <th class="px-3 py-2.5 text-right">Successful changes</th>
              <th class="px-3 py-2.5 text-right">Flagged drift</th>
              <th class="px-3 py-2.5">Last successful execution</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <tr v-for="row in deviceRows" :key="row.device.id" class="hover:bg-surface-raised">
              <td class="px-3 py-3">
                <RouterLink :to="{ name: 'device-detail', params: { id: row.device.id } }" class="font-medium text-text-primary hover:text-brand-600">
                  {{ row.device.name }}
                </RouterLink>
                <p class="mt-0.5 font-mono text-xs text-text-secondary">{{ row.device.management_ip }}</p>
              </td>
              <td class="px-3 py-3">
                <span class="rounded px-2 py-1 text-[11px] font-medium" :class="deviceHealth(row.device).class">{{ deviceHealth(row.device).label }}</span>
              </td>
              <td class="px-3 py-3 text-right font-semibold tabular-nums text-text-primary">{{ row.successCount }}</td>
              <td class="px-3 py-3 text-right tabular-nums" :class="row.flaggedCount ? 'font-semibold text-status-critical' : 'text-text-secondary'">{{ row.flaggedCount }}</td>
              <td class="px-3 py-3 text-xs text-text-secondary">{{ formatDate(row.latestSuccessAt) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div class="grid grid-cols-1 gap-8 xl:grid-cols-2">
      <section>
        <div class="mb-3 flex items-center justify-between">
          <div>
            <h2 class="text-base font-semibold text-text-primary">Your recent executions</h2>
            <p class="mt-0.5 text-xs text-text-secondary">Actions submitted by your account.</p>
          </div>
          <RouterLink :to="{ name: 'my-activity' }" class="text-xs font-medium text-brand-600 hover:text-brand-700">Full history <ArrowRight class="inline h-3.5 w-3.5" /></RouterLink>
        </div>
        <div v-if="loading" class="h-28 animate-pulse bg-surface-sunken" />
        <p v-else-if="recentRequests.length === 0" class="border-y border-border py-7 text-sm text-text-secondary">No change requests submitted yet.</p>
        <ul v-else class="divide-y divide-border border-y border-border">
          <li v-for="request in recentRequests" :key="request.id" class="flex items-center justify-between gap-3 py-3">
            <div class="min-w-0">
              <p class="truncate text-sm font-medium text-text-primary">{{ request.action_name }}</p>
              <p class="mt-0.5 text-xs text-text-secondary">{{ request.device_name }} · {{ formatDate(request.applied_at ?? request.requested_at) }}</p>
            </div>
            <span class="shrink-0 rounded px-2 py-1 text-[11px] font-medium" :class="request.status === 'SUCCESS' ? 'bg-status-healthy-bg text-status-healthy' : request.status === 'FAILED' ? 'bg-status-critical-bg text-status-critical' : 'bg-status-warning-bg text-status-warning'">
              {{ request.status === 'SUCCESS' ? 'Succeeded' : request.status === 'FAILED' ? 'Failed' : 'Pending' }}
            </span>
          </li>
        </ul>
        <p v-if="!loading && failedRequests.length" class="mt-2 flex items-center gap-1.5 text-xs text-status-critical">
          <CircleAlert class="h-3.5 w-3.5" /> {{ failedRequests.length }} failed execution{{ failedRequests.length === 1 ? '' : 's' }} in your history.
        </p>
      </section>

      <section>
        <div class="mb-3 flex items-center justify-between">
          <div>
            <h2 class="text-base font-semibold text-text-primary">Detected configuration changes</h2>
            <p class="mt-0.5 text-xs text-text-secondary">Observed on devices in your scope; these may be your actions or out-of-band edits.</p>
          </div>
          <RouterLink :to="{ name: 'changes' }" class="text-xs font-medium text-brand-600 hover:text-brand-700">Change log <ArrowRight class="inline h-3.5 w-3.5" /></RouterLink>
        </div>
        <div v-if="loading" class="h-28 animate-pulse bg-surface-sunken" />
        <p v-else-if="recentChanges.length === 0" class="border-y border-border py-7 text-sm text-text-secondary">No configuration drift detected on your devices.</p>
        <ul v-else class="divide-y divide-border border-y border-border">
          <li v-for="change in recentChanges" :key="change.id" class="flex items-center justify-between gap-3 py-3">
            <RouterLink :to="{ name: 'change-detail', params: { id: change.id } }" class="min-w-0 hover:text-brand-600">
              <p class="truncate text-sm font-medium text-text-primary">{{ change.device_name }}</p>
              <p class="mt-0.5 truncate text-xs text-text-secondary">{{ change.matched_concept_names.join(', ') || 'General configuration drift' }}</p>
            </RouterLink>
            <div class="flex shrink-0 items-center gap-2 text-xs">
              <span class="text-text-secondary">{{ new Date(change.detected_at).toLocaleDateString() }}</span>
              <span class="rounded px-2 py-1 font-medium" :class="change.status === 'FLAGGED' ? 'bg-status-critical-bg text-status-critical' : change.status === 'ACKNOWLEDGED' ? 'bg-status-healthy-bg text-status-healthy' : 'bg-status-neutral-bg text-status-neutral'">{{ change.status === 'FLAGGED' ? 'Flagged' : change.status === 'ACKNOWLEDGED' ? 'Reviewed' : 'Info' }}</span>
            </div>
          </li>
        </ul>
      </section>
    </div>

    <div class="flex items-center gap-2 border-t border-border pt-4 text-xs text-text-secondary">
      <Wrench class="h-3.5 w-3.5" /> {{ devices.length }} controlled device{{ devices.length === 1 ? '' : 's' }}
      <span class="text-border-strong">·</span>
      <GitCompareArrows class="h-3.5 w-3.5" /> {{ changes.length }} detected config change{{ changes.length === 1 ? '' : 's' }}
      <span class="text-border-strong">·</span>
      <Check class="h-3.5 w-3.5 text-status-healthy" /> {{ successfulRequests.length }} successful execution{{ successfulRequests.length === 1 ? '' : 's' }}
      <span class="ml-auto flex items-center gap-1"><Clock3 class="h-3.5 w-3.5" /> {{ pendingRequests.length }} pending</span>
    </div>
  </div>
</template>