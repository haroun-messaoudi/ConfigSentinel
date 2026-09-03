<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/features/auth/stores/auth.store'
import { alertsApi } from '../api/alerts.api'
import { useNotificationCounts } from '@/composables/useNotificationCounts'
import type { Alert } from '../types'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { CheckCircle2, AlertTriangle, ShieldAlert, Info } from 'lucide-vue-next'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const { refreshCounts } = useNotificationCounts()

type FilterTab = 'all' | 'undelivered' | 'delivered'

function initialFilter(): FilterTab {
  const q = route.query.filter
  if (q === 'all' || q === 'undelivered' || q === 'delivered') return q
  return 'undelivered'
}

const activeFilter = ref<FilterTab>(initialFilter())

const alerts = ref<Alert[]>([])
const isLoading = ref(true)
const loadError = ref<string | null>(null)
const actionErrors = ref<Record<number, string>>({})
const pendingIds = ref<Set<number>>(new Set())

async function loadAlerts() {
  isLoading.value = true
  loadError.value = null
  try {
    const delivered = activeFilter.value === 'all' ? undefined : activeFilter.value === 'delivered'
    alerts.value = await alertsApi.list(delivered)
  } catch {
    loadError.value = 'Could not load alerts. Please try again.'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadAlerts)

function setFilter(tab: FilterTab) {
  activeFilter.value = tab
  router.replace({ query: tab === 'all' ? {} : { filter: tab } })
  loadAlerts()
}

function severityMeta(severity: string) {
  const s = severity?.toLowerCase()
  if (s === 'high' || s === 'critical') return { class: 'bg-status-critical-bg text-status-critical', icon: ShieldAlert }
  if (s === 'medium') return { class: 'bg-status-warning-bg text-status-warning', icon: AlertTriangle }
  if (s === 'low') return { class: 'bg-status-neutral-bg text-status-neutral', icon: Info }
  return { class: 'bg-status-neutral-bg text-status-neutral', icon: Info }
}

async function markDelivered(alert: Alert) {
  delete actionErrors.value[alert.id]
  pendingIds.value.add(alert.id)
  try {
    const { data } = await alertsApi.markDelivered(alert.id)
    if (activeFilter.value === 'undelivered') {
      alerts.value = alerts.value.filter((a) => a.id !== alert.id)
    } else {
      Object.assign(alert, data)
    }
    refreshCounts()
  } catch {
    actionErrors.value[alert.id] = 'Could not mark as delivered.'
  } finally {
    pendingIds.value.delete(alert.id)
  }
}

// Clicking the device name is a shortcut: mark delivered (best-effort —
// still navigates even if this fails, since seeing the change matters more
// than the bookkeeping call succeeding) then jump straight to the change.
async function openChange(alert: Alert) {
  if (!alert.delivered) {
    try {
      await alertsApi.markDelivered(alert.id)
      refreshCounts()
    } catch {
      // ignore — navigation proceeds regardless
    }
  }
  router.push({ name: 'change-detail', params: { id: alert.change } })
}
</script>

<template>
  <div>
    <div class="mb-6">
      <h2 class="text-xl font-semibold text-text-primary">Alerts</h2>
      <p class="text-sm text-text-secondary mt-1">Notifications generated from detected config changes.</p>
    </div>

    <div class="border-b border-border mb-6">
      <nav class="flex gap-6">
        <button
          v-for="tab in (['undelivered', 'delivered', 'all'] as FilterTab[])"
          :key="tab"
          type="button"
          class="pb-3 text-sm font-medium border-b-2 -mb-px capitalize transition-colors cursor-pointer"
          :class="activeFilter === tab ? 'border-brand-500 text-brand-600' : 'border-transparent text-text-secondary hover:text-text-primary'"
          @click="setFilter(tab)"
        >
          {{ tab }}
        </button>
      </nav>
    </div>

    <ErrorAlert v-if="loadError" :message="loadError" class="mb-4" />
    <div v-if="isLoading" class="text-sm text-text-secondary">Loading alerts…</div>

    <div v-else-if="alerts.length === 0" class="bg-surface-raised border border-border rounded-lg p-8 text-center">
      <p class="text-sm text-text-secondary">No alerts here.</p>
    </div>

    <div v-else class="bg-surface-raised border border-border rounded-lg overflow-hidden shadow-sm">
      <table class="w-full text-sm">
        <thead class="bg-surface-sunken text-left text-xs font-medium uppercase tracking-wide text-text-secondary">
          <tr>
            <th class="px-4 py-3">Device</th>
            <th class="px-4 py-3">Severity</th>
            <th class="px-4 py-3">Created</th>
            <th class="px-4 py-3">Status</th>
            <th v-if="auth.hasRole('admin', 'operator')" class="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-for="alert in alerts" :key="alert.id" class="hover:bg-surface-sunken">
            <td class="px-4 py-3 font-medium text-text-primary">
              <button
                type="button"
                title="Open the related change (marks this alert delivered)"
                class="hover:underline hover:text-brand-600 text-left cursor-pointer"
                @click="openChange(alert)"
              >
                {{ alert.device_name }}
              </button>
            </td>
            <td class="px-4 py-3">
              <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium capitalize" :class="severityMeta(alert.severity).class">
                <component :is="severityMeta(alert.severity).icon" class="w-3 h-3" />
                {{ alert.severity || 'Unknown' }}
              </span>
            </td>
            <td class="px-4 py-3 text-text-secondary">{{ new Date(alert.created_at).toLocaleString() }}</td>
            <td class="px-4 py-3">
              <span
                class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
                :class="alert.delivered ? 'bg-status-healthy-bg text-status-healthy' : 'bg-status-neutral-bg text-status-neutral'"
              >
                <CheckCircle2 v-if="alert.delivered" class="w-3 h-3" />
                {{ alert.delivered ? 'Delivered' : 'Undelivered' }}
              </span>
            </td>
            <td v-if="auth.hasRole('admin', 'operator')" class="px-4 py-3 text-right">
              <button
                v-if="!alert.delivered"
                type="button"
                title="Mark as delivered without opening the change"
                class="rounded px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-500/10 cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="pendingIds.has(alert.id)"
                @click="markDelivered(alert)"
              >
                Mark Delivered
              </button>
              <p v-if="actionErrors[alert.id]" class="mt-1 text-xs text-status-critical">{{ actionErrors[alert.id] }}</p>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>