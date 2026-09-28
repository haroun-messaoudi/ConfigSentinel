<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { actionsApi } from '@/features/actions/api/actions.api'
import type { ChangeRequestItem } from '@/features/actions/types'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { ArrowRight, CheckCircle2, ChevronDown, CircleAlert, Clock3, Terminal } from 'lucide-vue-next'

type StatusFilter = 'ALL' | ChangeRequestItem['status']

const route = useRoute()
const router = useRouter()
const requests = ref<ChangeRequestItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const activeFilter = ref<StatusFilter>('ALL')
const deviceFilter = ref(typeof route.query.device === 'string' ? route.query.device : 'ALL')

async function loadRequests() {
  loading.value = true
  error.value = null
  try {
    requests.value = await actionsApi.listChangeRequests()
    requests.value.sort((a, b) => new Date(b.requested_at).getTime() - new Date(a.requested_at).getTime())
  } catch {
    error.value = 'Could not load your change execution history.'
  } finally {
    loading.value = false
  }
}

onMounted(loadRequests)

const statusCounts = computed(() => ({
  SUCCESS: requests.value.filter((request) => request.status === 'SUCCESS').length,
  PENDING: requests.value.filter((request) => request.status === 'PENDING').length,
  FAILED: requests.value.filter((request) => request.status === 'FAILED').length,
}))

const deviceOptions = computed(() => {
  const unique = new Map<number, string>()
  for (const request of requests.value) unique.set(request.device, request.device_name)
  return Array.from(unique, ([id, name]) => ({ id: String(id), name })).sort((a, b) => a.name.localeCompare(b.name))
})

const visibleRequests = computed(() => requests.value.filter((request) => {
  const matchesStatus = activeFilter.value === 'ALL' || request.status === activeFilter.value
  const matchesDevice = deviceFilter.value === 'ALL' || String(request.device) === deviceFilter.value
  return matchesStatus && matchesDevice
}))

function setFilter(filter: StatusFilter) {
  activeFilter.value = filter
}

function setDeviceFilter(value: string) {
  deviceFilter.value = value
  router.replace({ query: value === 'ALL' ? {} : { device: value } })
}

function statusMeta(status: ChangeRequestItem['status']) {
  if (status === 'SUCCESS') return { label: 'Succeeded', class: 'bg-status-healthy-bg text-status-healthy', icon: CheckCircle2 }
  if (status === 'FAILED') return { label: 'Failed', class: 'bg-status-critical-bg text-status-critical', icon: CircleAlert }
  return { label: 'Pending', class: 'bg-status-warning-bg text-status-warning', icon: Clock3 }
}

function formatDate(value: string | undefined) {
  return value ? new Date(value).toLocaleString() : '—'
}
</script>

<template>
  <div class="space-y-7">
    <header class="flex flex-col gap-3 border-b border-border pb-5 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-xs font-semibold uppercase text-brand-600">Operator workspace</p>
        <h1 class="mt-1 text-2xl font-semibold text-text-primary">My change activity</h1>
        <p class="mt-1 text-sm text-text-secondary">Execution history for configuration changes submitted by your account.</p>
      </div>
      <div class="grid grid-cols-3 gap-5 text-right">
        <div><p class="text-[11px] text-text-secondary">Succeeded</p><p class="mt-0.5 text-lg font-semibold tabular-nums text-status-healthy">{{ statusCounts.SUCCESS }}</p></div>
        <div><p class="text-[11px] text-text-secondary">Pending</p><p class="mt-0.5 text-lg font-semibold tabular-nums text-status-warning">{{ statusCounts.PENDING }}</p></div>
        <div><p class="text-[11px] text-text-secondary">Failed</p><p class="mt-0.5 text-lg font-semibold tabular-nums text-status-critical">{{ statusCounts.FAILED }}</p></div>
      </div>
    </header>

    <ErrorAlert v-if="error" :message="error" />

    <div class="flex flex-col gap-3 border-b border-border pb-3 sm:flex-row sm:items-center sm:justify-between">
      <div class="inline-flex w-fit border-b border-border">
        <button
          v-for="filter in (['ALL', 'SUCCESS', 'PENDING', 'FAILED'] as StatusFilter[])"
          :key="filter"
          type="button"
          class="border-b-2 px-3 py-2 text-xs font-medium transition-colors"
          :class="activeFilter === filter ? 'border-brand-500 text-brand-600' : 'border-transparent text-text-secondary hover:text-text-primary'"
          @click="setFilter(filter)"
        >
          {{ filter === 'ALL' ? 'All activity' : filter === 'SUCCESS' ? 'Succeeded' : filter === 'PENDING' ? 'Pending' : 'Failed' }}
          <span class="ml-1 text-text-muted">{{ filter === 'ALL' ? requests.length : statusCounts[filter] }}</span>
        </button>
      </div>
      <label class="flex items-center gap-2 text-xs text-text-secondary">
        Device
        <select :value="deviceFilter" class="max-w-56 rounded-md border border-border bg-surface-raised px-2.5 py-2 text-xs text-text-primary" @change="setDeviceFilter(($event.target as HTMLSelectElement).value)">
          <option value="ALL">All assigned devices</option>
          <option v-for="device in deviceOptions" :key="device.id" :value="device.id">{{ device.name }}</option>
        </select>
      </label>
    </div>

    <div v-if="loading" class="space-y-3"><div v-for="row in 4" :key="row" class="h-16 animate-pulse bg-surface-sunken" /></div>
    <div v-else-if="visibleRequests.length === 0" class="border-y border-border py-12 text-center">
      <Terminal class="mx-auto h-6 w-6 text-text-muted" />
      <p class="mt-2 text-sm font-medium text-text-primary">No matching change activity</p>
      <p class="mt-1 text-xs text-text-secondary">Requests you submit will appear here with their execution result.</p>
    </div>
    <div v-else class="overflow-x-auto border-y border-border">
      <table class="w-full min-w-[780px] text-left text-sm">
        <thead class="border-b border-border bg-surface-sunken text-[11px] font-semibold uppercase text-text-secondary">
          <tr>
            <th class="px-3 py-2.5">Change</th>
            <th class="px-3 py-2.5">Device</th>
            <th class="px-3 py-2.5">Result</th>
            <th class="px-3 py-2.5">Submitted</th>
            <th class="px-3 py-2.5">Applied</th>
            <th class="px-3 py-2.5">Configuration</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-for="request in visibleRequests" :key="request.id" class="align-top">
            <td class="px-3 py-3 font-medium text-text-primary">{{ request.action_name }}</td>
            <td class="px-3 py-3">
              <RouterLink :to="{ name: 'device-detail', params: { id: request.device } }" class="font-medium text-brand-600 hover:text-brand-700">
                {{ request.device_name }} <ArrowRight class="inline h-3 w-3" />
              </RouterLink>
            </td>
            <td class="px-3 py-3">
              <span class="inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] font-medium" :class="statusMeta(request.status).class">
                <component :is="statusMeta(request.status).icon" class="h-3.5 w-3.5" /> {{ statusMeta(request.status).label }}
              </span>
              <p v-if="request.status === 'FAILED' && request.error_message" class="mt-1 max-w-52 text-xs text-status-critical">{{ request.error_message }}</p>
            </td>
            <td class="px-3 py-3 text-xs text-text-secondary">{{ formatDate(request.requested_at) }}</td>
            <td class="px-3 py-3 text-xs text-text-secondary">{{ formatDate(request.applied_at) }}</td>
            <td class="px-3 py-3">
              <details v-if="request.generated_commands" class="group">
                <summary class="flex cursor-pointer list-none items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700">
                  <ChevronDown class="h-3.5 w-3.5 transition-transform group-open:rotate-180" /> View commands
                </summary>
                <pre class="mt-2 max-w-[28rem] overflow-x-auto whitespace-pre-wrap rounded bg-surface-sunken p-3 font-mono text-[11px] text-text-primary">{{ request.generated_commands }}</pre>
              </details>
              <span v-else class="text-xs text-text-muted">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>