<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/features/auth/stores/auth.store'
import { devicesApi } from '../api/devices.api'
import { useCheckNow } from '../composables/useCheckNow'
import type { Device } from '../types'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import DeviceFormModal from './DeviceFormModal.vue'
import { Plus, RefreshCw, Pause, Play, Search, ChevronLeft, ChevronRight } from 'lucide-vue-next'

const auth = useAuthStore()
const router = useRouter()
const { checkingIds, checkErrors, checkNow } = useCheckNow()

const devices = ref<Device[]>([])
const isLoading = ref(true)
const loadError = ref<string | null>(null)
const showCreateModal = ref(false)
const actionErrors = ref<Record<number, string>>({})
const pendingActions = ref<Set<number>>(new Set())

// --- Search & Pagination ---
const searchQuery = ref('')
const currentPage = ref(1)
const itemsPerPage = 10

const filteredDevices = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()

  if (!query) {
    return devices.value
  }

  return devices.value.filter((device) => {
    return (
      device.name.toLowerCase().includes(query) ||
      device.management_ip.toLowerCase().includes(query) ||
      device.device_type.toLowerCase().includes(query)
    )
  })
})

const totalPages = computed(() => {
  return Math.max(1, Math.ceil(filteredDevices.value.length / itemsPerPage))
})

const paginatedDevices = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage
  return filteredDevices.value.slice(start, start + itemsPerPage)
})

const paginationStart = computed(() => {
  if (filteredDevices.value.length === 0) return 0
  return (currentPage.value - 1) * itemsPerPage + 1
})

const paginationEnd = computed(() => {
  return Math.min(currentPage.value * itemsPerPage, filteredDevices.value.length)
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const current = currentPage.value

  if (total <= 5) {
    return Array.from({ length: total }, (_, index) => index + 1)
  }

  if (current <= 3) {
    return [1, 2, 3, 4, 5]
  }

  if (current >= total - 2) {
    return [total - 4, total - 3, total - 2, total - 1, total]
  }

  return [current - 2, current - 1, current, current + 1, current + 2]
})

watch(searchQuery, () => {
  currentPage.value = 1
})

watch(totalPages, (newTotal) => {
  if (currentPage.value > newTotal) {
    currentPage.value = newTotal
  }
})

function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
}

async function loadDevices() {
  isLoading.value = true
  loadError.value = null

  try {
    devices.value = await devicesApi.list()
  } catch {
    loadError.value = 'Could not load devices. Please try again.'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadDevices)

function getStatusBadge(device: Device) {
  if (!device.is_active) {
    return {
      text: 'Paused',
      class: 'bg-status-neutral-bg text-status-neutral',
    }
  }

  if (device.last_poll_status === 'OK') {
    return {
      text: 'Healthy',
      class: 'bg-status-healthy-bg text-status-healthy',
    }
  }

  if (device.last_poll_status === 'ERROR') {
    return {
      text: 'Failing',
      class: 'bg-status-critical-bg text-status-critical',
    }
  }

  return {
    text: 'Never polled',
    class: 'bg-status-neutral-bg text-status-neutral',
  }
}

function goToDetail(device: Device) {
  router.push({
    name: 'device-detail',
    params: { id: device.id },
  })
}

async function runPauseResume(
  device: Device,
  action: 'pause' | 'resume',
) {
  delete actionErrors.value[device.id]

  pendingActions.value.add(device.id)

  try {
    if (action === 'pause') {
      Object.assign(
        device,
        (await devicesApi.pause(device.id)).data,
      )
    } else {
      Object.assign(
        device,
        (await devicesApi.resume(device.id)).data,
      )
    }
  } catch {
    actionErrors.value[device.id] =
      'Action failed. Please try again.'
  } finally {
    pendingActions.value.delete(device.id)
  }
}

function onDeviceSaved(device: Device) {
  devices.value = [device, ...devices.value]
  currentPage.value = 1
}
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-xl font-semibold text-text-primary">
          Devices
        </h2>

        <p class="text-sm text-text-secondary mt-1">
          Registry of monitored network devices.
        </p>
      </div>

      <BaseButton
        v-if="auth.hasRole('admin')"
        @click="showCreateModal = true"
      >
        <Plus class="w-4 h-4" />
        Add Device
      </BaseButton>
    </div>

    <ErrorAlert
      v-if="loadError"
      :message="loadError"
      class="mb-4"
    />

    <div
      v-if="isLoading"
      class="text-sm text-text-secondary"
    >
      Loading devices…
    </div>

    <div
      v-else-if="devices.length === 0"
      class="bg-surface-raised border border-border rounded-lg p-8 text-center"
    >
      <p class="text-sm text-text-secondary">
        No devices registered yet.
      </p>
    </div>

    <div v-else>
      <!-- Search -->
      <div class="flex items-center justify-between gap-4 mb-3">
        <div class="relative w-full max-w-sm">
          <Search
            class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted"
          />

          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search devices..."
            class="w-full rounded-md border border-border bg-surface-raised pl-9 pr-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500"
          />
        </div>

        <p class="text-xs text-text-secondary whitespace-nowrap">
          {{ filteredDevices.length }}
          {{ filteredDevices.length === 1 ? 'device' : 'devices' }}
        </p>
      </div>

      <!-- No search results -->
      <div
        v-if="filteredDevices.length === 0"
        class="bg-surface-raised border border-border rounded-lg p-8 text-center"
      >
        <p class="text-sm text-text-secondary">
          No devices match your search.
        </p>
      </div>

      <!-- Table -->
      <div
        v-else
        class="bg-surface-raised border border-border rounded-lg overflow-hidden shadow-sm"
      >
        <table class="w-full text-sm">
          <thead
            class="bg-surface-sunken text-left text-xs font-medium uppercase tracking-wide text-text-secondary border-b border-border"
          >
            <tr>
              <th class="px-4 py-3">Name</th>
              <th class="px-4 py-3">Management IP</th>
              <th class="px-4 py-3">Type</th>
              <th class="px-4 py-3">Status</th>
              <th class="px-4 py-3">Last Polled</th>
              <th
                v-if="auth.hasRole('admin', 'operator')"
                class="px-4 py-3 text-right"
              >
                Actions
              </th>
            </tr>
          </thead>

          <tbody class="divide-y divide-border">
            <tr
              v-for="device in paginatedDevices"
              :key="device.id"
              class="hover:bg-surface-sunken cursor-pointer"
              @click="goToDetail(device)"
            >
              <td class="px-4 py-3 font-medium text-text-primary">
                {{ device.name }}
              </td>

              <td class="px-4 py-3 text-text-secondary font-mono text-xs">
                {{ device.management_ip }}
              </td>

              <td class="px-4 py-3 text-text-secondary">
                {{ device.device_type }}
              </td>

              <td class="px-4 py-3">
                <span
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="getStatusBadge(device).class"
                >
                  {{ getStatusBadge(device).text }}
                </span>
              </td>

              <td class="px-4 py-3 text-text-secondary">
                {{
                  device.last_polled_at
                    ? new Date(device.last_polled_at).toLocaleString()
                    : '—'
                }}
              </td>

              <td
                v-if="auth.hasRole('admin', 'operator')"
                class="px-4 py-3"
                @click.stop
              >
                <div class="flex justify-end gap-2">
                  <button
                    type="button"
                    class="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-text-secondary hover:bg-surface-sunken disabled:opacity-50"
                    :disabled="checkingIds.has(device.id)"
                    @click="
                      checkNow(
                        device,
                        (updated) => Object.assign(device, updated),
                      )
                    "
                  >
                    <RefreshCw
                      class="w-3.5 h-3.5"
                      :class="{
                        'animate-spin': checkingIds.has(device.id),
                      }"
                    />

                    {{
                      checkingIds.has(device.id)
                        ? 'Checking…'
                        : 'Check Now'
                    }}
                  </button>

                  <button
                    type="button"
                    class="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-text-secondary hover:bg-surface-sunken disabled:opacity-50"
                    :disabled="pendingActions.has(device.id)"
                    @click="
                      runPauseResume(
                        device,
                        device.is_active ? 'pause' : 'resume',
                      )
                    "
                  >
                    <component
                      :is="device.is_active ? Pause : Play"
                      class="w-3.5 h-3.5"
                    />

                    {{
                      device.is_active
                        ? 'Pause'
                        : 'Resume'
                    }}
                  </button>
                </div>

                <p
                  v-if="actionErrors[device.id]"
                  class="mt-1 text-xs text-status-critical text-right"
                >
                  {{ actionErrors[device.id] }}
                </p>

                <p
                  v-if="checkErrors[device.id]"
                  class="mt-1 text-xs text-status-warning text-right"
                >
                  {{ checkErrors[device.id] }}
                </p>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Pagination -->
        <div
          v-if="totalPages > 1"
          class="flex items-center justify-between gap-4 border-t border-border px-4 py-3"
        >
          <p class="text-xs text-text-secondary">
            Showing
            <span class="font-medium text-text-primary">
              {{ paginationStart }}
            </span>
            –
            <span class="font-medium text-text-primary">
              {{ paginationEnd }}
            </span>
            of
            <span class="font-medium text-text-primary">
              {{ filteredDevices.length }}
            </span>
          </p>

          <div class="flex items-center gap-1">
            <button
              type="button"
              class="inline-flex items-center justify-center rounded-md border border-border px-2 py-1.5 text-xs text-text-secondary hover:bg-surface-sunken disabled:opacity-40 disabled:cursor-not-allowed"
              :disabled="currentPage === 1"
              @click="goToPage(currentPage - 1)"
            >
              <ChevronLeft class="w-4 h-4" />
            </button>

            <button
              v-for="page in visiblePages"
              :key="page"
              type="button"
              class="min-w-8 rounded-md px-2 py-1.5 text-xs font-medium transition-colors"
              :class="
                currentPage === page
                  ? 'bg-brand-500 text-white'
                  : 'text-text-secondary hover:bg-surface-sunken'
              "
              @click="goToPage(page)"
            >
              {{ page }}
            </button>

            <button
              type="button"
              class="inline-flex items-center justify-center rounded-md border border-border px-2 py-1.5 text-xs text-text-secondary hover:bg-surface-sunken disabled:opacity-40 disabled:cursor-not-allowed"
              :disabled="currentPage === totalPages"
              @click="goToPage(currentPage + 1)"
            >
              <ChevronRight class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <DeviceFormModal
      :open="showCreateModal"
      mode="create"
      @close="showCreateModal = false"
      @saved="onDeviceSaved"
    />
  </div>
</template>