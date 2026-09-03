<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/features/auth/stores/auth.store'
import { devicesApi } from '../api/devices.api'
import { snapshotsApi } from '@/features/snapshots/api/snapshots.api'
import type { Device } from '../types'
import type { Snapshot } from '@/features/snapshots/types'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import { Star, Eye } from 'lucide-vue-next'

const props = defineProps<{ id: string }>()
const router = useRouter()
const auth = useAuthStore()

const device = ref<Device | null>(null)
const snapshots = ref<Snapshot[]>([])
const isLoading = ref(true)
const loadError = ref<string | null>(null)

const viewingSnapshot = ref<Snapshot | null>(null)
const showViewModal = ref(false)

const baselineErrors = ref<Record<number, string>>({})
const pendingBaselineIds = ref<Set<number>>(new Set())

async function load() {
  isLoading.value = true
  loadError.value = null
  try {
    const [dev, snaps] = await Promise.all([devicesApi.get(props.id), snapshotsApi.listForDevice(props.id)])
    device.value = dev
    snapshots.value = snaps
  } catch {
    loadError.value = 'Could not load snapshot history.'
  } finally {
    isLoading.value = false
  }
}

onMounted(load)

function openSnapshot(snapshot: Snapshot) {
  viewingSnapshot.value = snapshot
  showViewModal.value = true
}

async function setAsBaseline(snapshot: Snapshot) {
  delete baselineErrors.value[snapshot.id]
  pendingBaselineIds.value.add(snapshot.id)
  try {
    const { data } = await snapshotsApi.setBaseline(snapshot.id)
    snapshots.value = snapshots.value.map((s) => ({
      ...s,
      is_baseline: s.id === data.id ? data.is_baseline : false,
    }))
  } catch {
    baselineErrors.value[snapshot.id] = 'Could not set as baseline.'
  } finally {
    pendingBaselineIds.value.delete(snapshot.id)
  }
}
</script>

<template>
  <div class="max-w-4xl">
    <button
      type="button"
      class="mb-4 text-sm text-text-secondary hover:text-text-primary"
      @click="router.push({ name: 'device-detail', params: { id: props.id } })"
    >
      ← Back to {{ device?.name ?? 'Device' }}
    </button>

    <div class="mb-6">
      <h2 class="text-xl font-semibold text-text-primary">Snapshot History</h2>
      <p class="text-sm text-text-secondary mt-1">
        Historical configuration pulls for <span class="font-medium text-text-primary">{{ device?.name ?? '…' }}</span>.
      </p>
    </div>
    <p v-if="device?.last_polled_at" class="text-xs text-text-muted mb-4">
      Last polled {{ new Date(device.last_polled_at).toLocaleString() }}
      <span v-if="device.last_poll_status === 'OK'">— no changes recorded if this is more recent than the newest snapshot below.</span>
    </p>
    <ErrorAlert v-if="loadError" :message="loadError" class="mb-4" />
    <div v-if="isLoading" class="text-sm text-text-secondary">Loading snapshots…</div>

    <div v-else-if="snapshots.length === 0" class="bg-surface-raised border border-border rounded-lg p-8 text-center">
      <p class="text-sm text-text-secondary">No snapshots recorded for this device yet.</p>
    </div>

    <div v-else class="bg-surface-raised border border-border rounded-lg overflow-hidden shadow-sm">
      <table class="w-full text-sm">
        <thead class="bg-surface-sunken text-left text-xs font-medium uppercase tracking-wide text-text-secondary">
          <tr>
            <th class="px-4 py-3">Taken At</th>
            <th class="px-4 py-3">Config Hash</th>
            <th class="px-4 py-3">Baseline</th>
            <th class="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-for="snapshot in snapshots" :key="snapshot.id" class="hover:bg-surface-sunken">
            <td class="px-4 py-3 font-medium text-text-primary">{{ new Date(snapshot.taken_at).toLocaleString() }}</td>
            <td class="px-4 py-3 text-text-secondary font-mono text-xs">{{ snapshot.config_hash.slice(0, 12) }}</td>
            <td class="px-4 py-3">
              <span
                v-if="snapshot.is_baseline"
                class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium bg-status-healthy-bg text-status-healthy"
              >
                <Star class="w-3 h-3" />
                Baseline
              </span>
              <span v-else class="text-text-muted text-xs">—</span>
            </td>
            <td class="px-4 py-3 text-right">
              <div class="flex justify-end gap-2 items-center">
                <button
                  type="button"
                  class="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-500/10"
                  @click="openSnapshot(snapshot)"
                >
                  <Eye class="w-3.5 h-3.5" />
                  View Config
                </button>
                <button
                  v-if="!snapshot.is_baseline && auth.hasRole('admin')"
                  type="button"
                  class="rounded px-2 py-1 text-xs font-medium text-text-secondary hover:bg-surface-sunken disabled:opacity-50"
                  :disabled="pendingBaselineIds.has(snapshot.id)"
                  @click="setAsBaseline(snapshot)"
                >
                  Set as Baseline
                </button>
              </div>
              <p v-if="baselineErrors[snapshot.id]" class="mt-1 text-xs text-status-critical text-right">
                {{ baselineErrors[snapshot.id] }}
              </p>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <BaseModal
      :open="showViewModal"
      :title="viewingSnapshot ? `Config — ${new Date(viewingSnapshot.taken_at).toLocaleString()}` : 'Config'"
      @close="showViewModal = false"
    >
      <pre class="text-xs font-mono bg-surface-sunken text-text-primary rounded-md p-4 overflow-x-auto max-h-[60vh] whitespace-pre-wrap">{{ viewingSnapshot?.raw_text }}</pre>
    </BaseModal>
  </div>
</template>