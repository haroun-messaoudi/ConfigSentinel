<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { actionsApi } from '@/features/actions/api/actions.api'
import type { ChangeRequestItem } from '@/features/actions/types'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { Activity, CheckCircle2, CircleAlert, Clock3, RefreshCw, Wrench } from 'lucide-vue-next'

const requests = ref<ChangeRequestItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

async function loadRequests() {
  loading.value = true
  error.value = null
  try {
    requests.value = await actionsApi.listChangeRequests()
    requests.value.sort((a, b) => new Date(b.requested_at).getTime() - new Date(a.requested_at).getTime())
  } catch {
    error.value = 'Could not load change execution activity.'
  } finally {
    loading.value = false
  }
}

onMounted(loadRequests)

const totals = computed(() => ({
  SUCCESS: requests.value.filter((request) => request.status === 'SUCCESS').length,
  PENDING: requests.value.filter((request) => request.status === 'PENDING').length,
  FAILED: requests.value.filter((request) => request.status === 'FAILED').length,
}))

const operatorActivity = computed(() => {
  const byUser = new Map<string, { name: string; total: number; success: number; pending: number; failed: number }>()
  for (const request of requests.value) {
    const name = request.requested_by_username || `User #${request.requested_by}`
    const summary = byUser.get(name) ?? { name, total: 0, success: 0, pending: 0, failed: 0 }
    summary.total += 1
    if (request.status === 'SUCCESS') summary.success += 1
    if (request.status === 'PENDING') summary.pending += 1
    if (request.status === 'FAILED') summary.failed += 1
    byUser.set(name, summary)
  }
  return Array.from(byUser.values()).sort((a, b) => b.total - a.total).slice(0, 6)
})

const recentRequests = computed(() => requests.value.slice(0, 7))

function statusMeta(status: ChangeRequestItem['status']) {
  if (status === 'SUCCESS') return { label: 'Succeeded', class: 'bg-status-healthy-bg text-status-healthy' }
  if (status === 'FAILED') return { label: 'Failed', class: 'bg-status-critical-bg text-status-critical' }
  return { label: 'Pending', class: 'bg-status-warning-bg text-status-warning' }
}

function formatDate(value: string | undefined) {
  return value ? new Date(value).toLocaleString() : '—'
}
</script>

<template>
  <section class="border-y border-border bg-surface-raised">
    <header class="flex flex-col gap-3 border-b border-border px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div class="flex items-start gap-3">
        <span class="mt-0.5 inline-flex h-8 w-8 items-center justify-center rounded bg-brand-500/10 text-brand-600"><Activity class="h-4 w-4" /></span>
        <div>
          <h2 class="text-base font-semibold text-text-primary">Configuration change operations</h2>
          <p class="mt-0.5 text-xs text-text-secondary">Execution outcomes and operator attribution across the fleet.</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button type="button" title="Refresh execution activity" class="rounded-md border border-border p-2 text-text-secondary hover:bg-surface-sunken" :disabled="loading" @click="loadRequests">
          <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': loading }" />
        </button>
        <RouterLink :to="{ name: 'actions-governance' }" class="inline-flex items-center gap-1.5 rounded-md bg-brand-600 px-3 py-2 text-xs font-medium text-white hover:bg-brand-700">
          <Wrench class="h-3.5 w-3.5" /> Manage permissions
        </RouterLink>
      </div>
    </header>

    <ErrorAlert v-if="error" :message="error" class="m-4" />

    <div class="grid grid-cols-3 divide-x divide-border border-b border-border">
      <div class="px-4 py-3">
        <p class="flex items-center gap-1.5 text-[11px] font-medium text-text-secondary"><CheckCircle2 class="h-3.5 w-3.5 text-status-healthy" /> Successful</p>
        <p class="mt-1 text-xl font-semibold tabular-nums text-text-primary">{{ loading ? '—' : totals.SUCCESS }}</p>
      </div>
      <div class="px-4 py-3">
        <p class="flex items-center gap-1.5 text-[11px] font-medium text-text-secondary"><Clock3 class="h-3.5 w-3.5 text-status-warning" /> Pending</p>
        <p class="mt-1 text-xl font-semibold tabular-nums text-text-primary">{{ loading ? '—' : totals.PENDING }}</p>
      </div>
      <div class="px-4 py-3">
        <p class="flex items-center gap-1.5 text-[11px] font-medium text-text-secondary"><CircleAlert class="h-3.5 w-3.5 text-status-critical" /> Failed</p>
        <p class="mt-1 text-xl font-semibold tabular-nums text-text-primary">{{ loading ? '—' : totals.FAILED }}</p>
      </div>
    </div>

    <div class="grid grid-cols-1 divide-y divide-border xl:grid-cols-3 xl:divide-x xl:divide-y-0">
      <div class="min-w-0 p-4 xl:col-span-2">
        <h3 class="mb-3 text-xs font-semibold uppercase text-text-secondary">Recent execution requests</h3>
        <div v-if="loading" class="space-y-2"><div v-for="row in 4" :key="row" class="h-9 animate-pulse bg-surface-sunken" /></div>
        <p v-else-if="recentRequests.length === 0" class="py-8 text-center text-sm text-text-secondary">No change requests have been submitted.</p>
        <div v-else class="overflow-x-auto">
          <table class="w-full min-w-[620px] text-left text-xs">
            <thead class="border-b border-border text-[10px] font-semibold uppercase text-text-muted">
              <tr><th class="py-2 pr-3">Action / Device</th><th class="py-2 pr-3">Requested by</th><th class="py-2 pr-3">Submitted</th><th class="py-2">Result</th></tr>
            </thead>
            <tbody class="divide-y divide-border">
              <tr v-for="request in recentRequests" :key="request.id" class="align-top">
                <td class="py-2.5 pr-3">
                  <p class="font-medium text-text-primary">{{ request.action_name }}</p>
                  <p class="mt-0.5 text-text-secondary">{{ request.device_name }}</p>
                </td>
                <td class="py-2.5 pr-3 font-medium text-text-primary">{{ request.requested_by_username }}</td>
                <td class="whitespace-nowrap py-2.5 pr-3 text-text-secondary">{{ formatDate(request.requested_at) }}</td>
                <td class="py-2.5"><span class="rounded px-2 py-1 text-[10px] font-semibold" :class="statusMeta(request.status).class">{{ statusMeta(request.status).label }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="min-w-0 p-4">
        <h3 class="mb-3 text-xs font-semibold uppercase text-text-secondary">Operator activity</h3>
        <div v-if="loading" class="space-y-3"><div v-for="row in 4" :key="row" class="h-8 animate-pulse bg-surface-sunken" /></div>
        <p v-else-if="operatorActivity.length === 0" class="py-8 text-center text-sm text-text-secondary">No operator activity yet.</p>
        <ul v-else class="divide-y divide-border">
          <li v-for="operator in operatorActivity" :key="operator.name" class="flex items-center justify-between gap-3 py-2.5">
            <div class="min-w-0">
              <p class="truncate text-xs font-semibold text-text-primary">{{ operator.name }}</p>
              <p class="mt-0.5 text-[10px] text-text-secondary">{{ operator.total }} request{{ operator.total === 1 ? '' : 's' }} · {{ operator.success }} succeeded</p>
            </div>
            <span v-if="operator.failed" class="shrink-0 rounded bg-status-critical-bg px-1.5 py-1 text-[10px] font-medium text-status-critical">{{ operator.failed }} failed</span>
            <span v-else-if="operator.pending" class="shrink-0 rounded bg-status-warning-bg px-1.5 py-1 text-[10px] font-medium text-status-warning">{{ operator.pending }} pending</span>
            <CheckCircle2 v-else class="h-4 w-4 shrink-0 text-status-healthy" />
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>