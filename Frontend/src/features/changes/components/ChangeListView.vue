<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { changesApi } from '../api/changes.api'
import type { ConfigChange, ChangeStatus } from '../types'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { ShieldAlert, CheckCircle2, Info } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()

type StatusFilter = 'all' | ChangeStatus

function initialFilter(): StatusFilter {
  const q = route.query.status
  if (q === 'FLAGGED' || q === 'INFORMATIONAL' || q === 'ACKNOWLEDGED') return q
  return 'FLAGGED'
}

const activeFilter = ref<StatusFilter>(initialFilter())

const changes = ref<ConfigChange[]>([])
const isLoading = ref(true)
const loadError = ref<string | null>(null)

const TAB_LABELS: Record<StatusFilter, string> = {
  FLAGGED: 'Flagged',
  INFORMATIONAL: 'Informational',
  ACKNOWLEDGED: 'Acknowledged',
  all: 'All',
}

async function loadChanges() {
  isLoading.value = true
  loadError.value = null
  try {
    const status = activeFilter.value === 'all' ? undefined : activeFilter.value
    changes.value = await changesApi.list({ status })
  } catch {
    loadError.value = 'Could not load config changes. Please try again.'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadChanges)

function setFilter(tab: StatusFilter) {
  activeFilter.value = tab
  router.replace({ query: tab === 'all' ? {} : { status: tab } })
  loadChanges()
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

function goToDetail(change: ConfigChange) {
  router.push({ name: 'change-detail', params: { id: change.id } })
}
</script>

<template>
  <div>
    <div class="mb-6">
      <h2 class="text-xl font-semibold text-text-primary">Config Changes</h2>
      <p class="text-sm text-text-secondary mt-1">Detected configuration drift across your devices.</p>
    </div>

    <div class="border-b border-border mb-6">
      <nav class="flex gap-6">
        <button
          v-for="tab in (['FLAGGED', 'INFORMATIONAL', 'ACKNOWLEDGED', 'all'] as StatusFilter[])"
          :key="tab"
          type="button"
          class="pb-3 text-sm font-medium border-b-2 -mb-px transition-colors"
          :class="activeFilter === tab ? 'border-brand-500 text-brand-600' : 'border-transparent text-text-secondary hover:text-text-primary'"
          @click="setFilter(tab)"
        >
          {{ TAB_LABELS[tab] }}
        </button>
      </nav>
    </div>

    <ErrorAlert v-if="loadError" :message="loadError" class="mb-4" />
    <div v-if="isLoading" class="text-sm text-text-secondary">Loading changes…</div>

    <div v-else-if="changes.length === 0" class="bg-surface-raised border border-border rounded-lg p-8 text-center">
      <p class="text-sm text-text-secondary">No config changes here.</p>
    </div>

    <div v-else class="bg-surface-raised border border-border rounded-lg overflow-hidden shadow-sm">
      <table class="w-full text-sm">
        <thead class="bg-surface-sunken text-left text-xs font-medium uppercase tracking-wide text-text-secondary">
          <tr>
            <th class="px-4 py-3">Device</th>
            <th class="px-4 py-3">Severity</th>
            <th class="px-4 py-3">Matched Concepts</th>
            <th class="px-4 py-3">Detected</th>
            <th class="px-4 py-3">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-for="change in changes" :key="change.id" class="hover:bg-surface-sunken cursor-pointer" @click="goToDetail(change)">
            <td class="px-4 py-3 font-medium text-text-primary">{{ change.device_name }}</td>
            <td class="px-4 py-3">
              <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium" :class="severityClass(change.severity_name)">
                {{ change.severity_name || 'None' }}
              </span>
            </td>
            <td class="px-4 py-3 text-text-secondary">
              {{ change.matched_concept_names.length ? change.matched_concept_names.join(', ') : '—' }}
            </td>
            <td class="px-4 py-3 text-text-secondary">{{ new Date(change.detected_at).toLocaleString() }}</td>
            <td class="px-4 py-3">
              <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium" :class="statusMeta(change.status).class">
                <component :is="statusMeta(change.status).icon" class="w-3 h-3" />
                {{ TAB_LABELS[change.status] }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>