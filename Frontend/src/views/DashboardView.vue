<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { RouterLink } from 'vue-router'
import {
  Server,
  ShieldAlert,
  Bell,
  ShieldCheck,
  ArrowRight,
  Activity,
  CheckCircle2,
  PauseCircle,
  Clock,
  WifiOff,
} from 'lucide-vue-next'
import { Line, Doughnut, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  CategoryScale,
  ArcElement,
  BarElement,
  Filler,
} from 'chart.js'

import { devicesApi } from '@/features/devices/api/devices.api'
import { changesApi } from '@/features/changes/api/changes.api'
import { alertsApi } from '@/features/alerts/api/alerts.api'
import { useDarkMode } from '@/composables/useDarkMode'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import type { Device } from '@/features/devices/types'
import type { ConfigChange } from '@/features/changes/types'
import type { Alert } from '@/features/alerts/types'

ChartJS.register(Title, Tooltip, Legend, LineElement, LinearScale, PointElement, CategoryScale, ArcElement, BarElement, Filler)

const { isDark } = useDarkMode()

const loading = ref(true)
const loadError = ref<string | null>(null)
const devices = ref<Device[]>([])
const changes = ref<ConfigChange[]>([])
const alerts = ref<Alert[]>([])

async function fetchData() {
  loading.value = true
  loadError.value = null
  try {
    const [devicesRes, changesRes, alertsRes] = await Promise.all([
      devicesApi.list(),
      changesApi.list(),
      alertsApi.list(),
    ])
    devices.value = devicesRes
    changes.value = changesRes
    alerts.value = alertsRes
  } catch {
    loadError.value = 'Could not load dashboard data. Please try again.'
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)

// --- KPIs ---
const stats = computed(() => {
  const totalDevices = devices.value.length
  const flaggedChanges = changes.value.filter((c) => c.status === 'FLAGGED').length
  const undeliveredAlerts = alerts.value.filter((a) => !a.delivered).length
  const acknowledgedChanges = changes.value.filter((c) => c.status === 'ACKNOWLEDGED').length

  const actionableTotal = flaggedChanges + acknowledgedChanges
  const complianceRate = actionableTotal > 0 ? Math.round((acknowledgedChanges / actionableTotal) * 100) : 100

  return { totalDevices, flaggedChanges, undeliveredAlerts, complianceRate }
})

// --- Fleet health breakdown ---
const fleetHealth = computed(() => {
  const total = devices.value.length
  const healthy = devices.value.filter((d) => d.is_active && d.last_poll_status === 'OK').length
  const failing = devices.value.filter((d) => d.is_active && d.last_poll_status === 'ERROR').length
  const paused = devices.value.filter((d) => !d.is_active).length
  const neverPolled = devices.value.filter((d) => d.is_active && !d.last_poll_status).length
  return { total, healthy, failing, paused, neverPolled }
})

// --- Devices needing attention: currently failing to poll, worst first.
// Distinct concern from config drift — this is connectivity/poll health. ---
const devicesNeedingAttention = computed(() =>
  devices.value
    .filter((d) => d.is_active && d.last_poll_status === 'ERROR')
    .sort((a, b) => b.consecutive_failures - a.consecutive_failures)
    .slice(0, 5),
)

const recentFlaggedChanges = computed(() => changes.value.filter((c) => c.status === 'FLAGGED').slice(0, 5))

// --- Top devices by drift volume: which devices generate the most
// config changes (flagged + acknowledged — informational excluded since
// it's noise, not drift). Classic "what's unstable" signal. ---
const topDriftDevices = computed(() => {
  const counts: Record<string, number> = {}
  changes.value.forEach((c) => {
    if (c.status === 'INFORMATIONAL') return
    counts[c.device_name] = (counts[c.device_name] || 0) + 1
  })
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
})

// --- Chart color resolution ---
function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

const chartColors = computed(() => {
  void isDark.value
  return {
    brand: cssVar('--color-brand-500'),
    brandFill: isDark.value ? 'rgba(59, 158, 218, 0.12)' : 'rgba(0, 115, 198, 0.08)',
    critical: cssVar('--color-status-critical'),
    warning: cssVar('--color-status-warning'),
    info: cssVar('--color-status-info'),
    neutral: cssVar('--color-status-neutral'),
    surfaceRaised: cssVar('--color-surface-raised'),
    border: cssVar('--color-border'),
    textSecondary: cssVar('--color-text-secondary'),
  }
})

const lineChartData = computed(() => {
  const countsByDate: Record<string, number> = {}
  const sorted = [...changes.value].sort((a, b) => new Date(a.detected_at).getTime() - new Date(b.detected_at).getTime())

  sorted.forEach((c) => {
    if (!c.detected_at) return
    const dateStr = new Date(c.detected_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    countsByDate[dateStr] = (countsByDate[dateStr] || 0) + 1
  })

  const labels = Object.keys(countsByDate)
  return {
    labels: labels.length > 0 ? labels : ['No Data'],
    datasets: [
      {
        label: 'Changes Detected',
        data: labels.length > 0 ? Object.values(countsByDate) : [0],
        borderColor: chartColors.value.brand,
        backgroundColor: chartColors.value.brandFill,
        tension: 0.35,
        fill: true,
        pointBackgroundColor: chartColors.value.brand,
      },
    ],
  }
})

const axisOptions = computed(() => ({
  x: {
    ticks: { color: chartColors.value.textSecondary, font: { size: 11 } },
    grid: { color: chartColors.value.border },
  },
  y: {
    ticks: { color: chartColors.value.textSecondary, font: { size: 11 }, precision: 0 },
    grid: { color: chartColors.value.border },
  },
}))

const lineChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: axisOptions.value,
}))

const doughnutChartData = computed(() => {
  const severityCounts: Record<string, number> = { High: 0, Medium: 0, Low: 0, Informational: 0 }

  changes.value.forEach((c) => {
    const rawSev = c.severity_name || 'Informational'
    const key = rawSev.charAt(0).toUpperCase() + rawSev.slice(1).toLowerCase()
    if (severityCounts[key] !== undefined) severityCounts[key]++
    else severityCounts['Informational']++
  })

  return {
    labels: ['High', 'Medium', 'Low', 'Informational'],
    datasets: [
      {
        data: [severityCounts['High'], severityCounts['Medium'], severityCounts['Low'], severityCounts['Informational']],
        backgroundColor: [chartColors.value.critical, chartColors.value.warning, chartColors.value.info, chartColors.value.neutral],
        borderWidth: 2,
        borderColor: chartColors.value.surfaceRaised,
      },
    ],
  }
})

const doughnutChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: 'bottom' as const,
      labels: { color: chartColors.value.textSecondary, font: { size: 11 }, boxWidth: 10, padding: 12 },
    },
  },
}))

const topDriftChartData = computed(() => ({
  labels: topDriftDevices.value.map(([name]) => name),
  datasets: [
    {
      label: 'Changes',
      data: topDriftDevices.value.map(([, count]) => count),
      backgroundColor: chartColors.value.warning,
      borderRadius: 4,
      barThickness: 18,
    },
  ],
}))

const topDriftChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: 'y' as const,
  plugins: { legend: { display: false } },
  scales: {
    x: {
      ticks: { color: chartColors.value.textSecondary, font: { size: 11 }, precision: 0 },
      grid: { color: chartColors.value.border },
    },
    y: {
      ticks: { color: chartColors.value.textSecondary, font: { size: 11 } },
      grid: { display: false },
    },
  },
}))
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-text-primary">Dashboard</h1>
        <p class="text-sm text-text-secondary mt-0.5">Real-time infrastructure drift & security posture</p>
      </div>
      <button
        @click="fetchData"
        class="flex items-center gap-2 px-3 py-1.5 bg-status-healthy-bg hover:opacity-90 text-status-healthy text-xs font-semibold rounded-full border border-status-healthy/20 transition-opacity cursor-pointer"
      >
        <Activity class="w-3.5 h-3.5" :class="{ 'animate-pulse': loading }" />
        {{ loading ? 'Updating...' : 'Monitoring Active' }}
      </button>
    </div>

    <ErrorAlert v-if="loadError" :message="loadError" />

    <!-- KPI Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <RouterLink
        to="/devices"
        class="bg-surface-raised p-5 rounded-xl border border-border shadow-sm flex items-center justify-between hover:border-brand-500/50 hover:shadow-md transition-all group"
      >
        <div>
          <p class="text-xs font-semibold text-text-secondary uppercase tracking-wider">Monitored Devices</p>
          <span v-if="loading" class="inline-block h-7 w-10 mt-2 rounded bg-surface-sunken animate-pulse" />
          <p v-else class="text-2xl font-bold text-text-primary mt-1">{{ stats.totalDevices }}</p>
        </div>
        <div class="p-3 bg-brand-50 dark:bg-brand-500/10 text-brand-600 rounded-lg group-hover:bg-brand-500 group-hover:text-white transition-colors">
          <Server class="w-5 h-5" />
        </div>
      </RouterLink>

      <RouterLink
        to="/changes?status=FLAGGED"
        class="bg-surface-raised p-5 rounded-xl border border-border shadow-sm flex items-center justify-between hover:border-status-warning/50 hover:shadow-md transition-all group"
      >
        <div>
          <p class="text-xs font-semibold text-text-secondary uppercase tracking-wider">Flagged Changes</p>
          <span v-if="loading" class="inline-block h-7 w-10 mt-2 rounded bg-surface-sunken animate-pulse" />
          <p v-else class="text-2xl font-bold text-status-warning mt-1">{{ stats.flaggedChanges }}</p>
        </div>
        <div class="p-3 bg-status-warning-bg text-status-warning rounded-lg group-hover:bg-status-warning group-hover:text-white transition-colors">
          <ShieldAlert class="w-5 h-5" />
        </div>
      </RouterLink>

      <RouterLink
        to="/alerts?filter=undelivered"
        class="bg-surface-raised p-5 rounded-xl border border-border shadow-sm flex items-center justify-between hover:border-status-critical/50 hover:shadow-md transition-all group"
      >
        <div>
          <p class="text-xs font-semibold text-text-secondary uppercase tracking-wider">Undelivered Alerts</p>
          <span v-if="loading" class="inline-block h-7 w-10 mt-2 rounded bg-surface-sunken animate-pulse" />
          <p v-else class="text-2xl font-bold text-status-critical mt-1">{{ stats.undeliveredAlerts }}</p>
        </div>
        <div class="p-3 bg-status-critical-bg text-status-critical rounded-lg group-hover:bg-status-critical group-hover:text-white transition-colors">
          <Bell class="w-5 h-5" />
        </div>
      </RouterLink>

      <RouterLink
        to="/changes?status=ACKNOWLEDGED"
        class="bg-surface-raised p-5 rounded-xl border border-border shadow-sm hover:border-status-healthy/50 hover:shadow-md transition-all group"
      >
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs font-semibold text-text-secondary uppercase tracking-wider">Audit Rate</p>
            <span v-if="loading" class="inline-block h-7 w-14 mt-2 rounded bg-surface-sunken animate-pulse" />
            <p v-else class="text-2xl font-bold text-status-healthy mt-1">{{ stats.complianceRate }}%</p>
          </div>
          <div class="p-3 bg-status-healthy-bg text-status-healthy rounded-lg group-hover:bg-status-healthy group-hover:text-white transition-colors">
            <ShieldCheck class="w-5 h-5" />
          </div>
        </div>
        <div v-if="!loading" class="mt-3 h-1.5 rounded-full bg-surface-sunken overflow-hidden">
          <div class="h-full bg-status-healthy rounded-full transition-all" :style="{ width: `${stats.complianceRate}%` }" />
        </div>
      </RouterLink>
    </div>

    <!-- Fleet Health -->
    <div class="bg-surface-raised rounded-xl border border-border shadow-sm p-5">
      <h3 class="text-sm font-semibold text-text-primary mb-4">Fleet Health</h3>

      <div v-if="loading" class="h-2 rounded-full bg-surface-sunken animate-pulse" />
      <template v-else-if="fleetHealth.total > 0">
        <div class="flex h-2 rounded-full overflow-hidden mb-4">
          <div class="bg-status-healthy" :style="{ width: `${(fleetHealth.healthy / fleetHealth.total) * 100}%` }" />
          <div class="bg-status-critical" :style="{ width: `${(fleetHealth.failing / fleetHealth.total) * 100}%` }" />
          <div class="bg-status-neutral" :style="{ width: `${(fleetHealth.paused / fleetHealth.total) * 100}%` }" />
          <div class="bg-status-warning" :style="{ width: `${(fleetHealth.neverPolled / fleetHealth.total) * 100}%` }" />
        </div>
        <div class="flex flex-wrap gap-x-6 gap-y-2 text-xs">
          <div class="flex items-center gap-1.5 text-text-secondary">
            <CheckCircle2 class="w-3.5 h-3.5 text-status-healthy" />
            <span class="font-medium text-text-primary">{{ fleetHealth.healthy }}</span> Healthy
          </div>
          <div class="flex items-center gap-1.5 text-text-secondary">
            <ShieldAlert class="w-3.5 h-3.5 text-status-critical" />
            <span class="font-medium text-text-primary">{{ fleetHealth.failing }}</span> Failing
          </div>
          <div class="flex items-center gap-1.5 text-text-secondary">
            <PauseCircle class="w-3.5 h-3.5 text-status-neutral" />
            <span class="font-medium text-text-primary">{{ fleetHealth.paused }}</span> Paused
          </div>
          <div class="flex items-center gap-1.5 text-text-secondary">
            <Clock class="w-3.5 h-3.5 text-status-warning" />
            <span class="font-medium text-text-primary">{{ fleetHealth.neverPolled }}</span> Never Polled
          </div>
        </div>
      </template>
      <p v-else class="text-xs text-text-muted">No devices registered yet.</p>
    </div>

    <!-- Actionable panels: config drift needing review + devices failing to poll -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 bg-surface-raised rounded-xl border border-border shadow-sm p-5">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h3 class="text-sm font-semibold text-text-primary">Action Required: Flagged Changes</h3>
            <p class="text-xs text-text-secondary mt-0.5">Unacknowledged configuration drift requiring technical audit</p>
          </div>
          <RouterLink to="/changes?status=FLAGGED" class="text-xs font-semibold text-brand-600 hover:text-brand-700 flex items-center gap-1 shrink-0">
            View all <ArrowRight class="w-3.5 h-3.5" />
          </RouterLink>
        </div>

        <div v-if="loading" class="space-y-3">
          <div v-for="i in 3" :key="i" class="h-12 rounded-lg bg-surface-sunken animate-pulse" />
        </div>

        <div v-else-if="recentFlaggedChanges.length === 0" class="text-center py-8 text-text-muted text-xs">
          No pending flagged changes requiring review.
        </div>

        <div v-else class="divide-y divide-border">
          <div v-for="change in recentFlaggedChanges" :key="change.id" class="py-3 flex items-center justify-between gap-4">
            <div class="space-y-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="font-semibold text-xs text-text-primary truncate">{{ change.device_name || `Device #${change.device}` }}</span>
                <span class="shrink-0 px-2 py-0.5 text-[10px] font-semibold rounded-full bg-status-critical-bg text-status-critical border border-status-critical/20">
                  {{ change.severity_name || 'Flagged' }}
                </span>
              </div>
              <p class="text-xs text-text-secondary truncate">
                <span class="text-text-primary font-medium">{{ change.matched_concept_names?.join(', ') || 'General Drift' }}</span>
              </p>
            </div>

            <RouterLink
              :to="`/changes/${change.id}`"
              class="shrink-0 px-3 py-1.5 text-xs font-semibold text-text-primary bg-surface-sunken hover:bg-border border border-border rounded-lg transition-colors"
            >
              Review
            </RouterLink>
          </div>
        </div>
      </div>

      <div class="bg-surface-raised rounded-xl border border-border shadow-sm p-5">
        <div class="mb-4">
          <h3 class="text-sm font-semibold text-text-primary">Devices Needing Attention</h3>
          <p class="text-xs text-text-secondary mt-0.5">Failing to poll — connectivity, not config drift</p>
        </div>

        <div v-if="loading" class="space-y-3">
          <div v-for="i in 3" :key="i" class="h-10 rounded-lg bg-surface-sunken animate-pulse" />
        </div>

        <div v-else-if="devicesNeedingAttention.length === 0" class="text-center py-8 text-text-muted text-xs">
          <CheckCircle2 class="w-6 h-6 mx-auto mb-2 text-status-healthy" />
          All active devices polling normally.
        </div>

        <div v-else class="divide-y divide-border">
          <RouterLink
            v-for="d in devicesNeedingAttention"
            :key="d.id"
            :to="{ name: 'device-detail', params: { id: d.id } }"
            class="py-2.5 flex items-center justify-between gap-2 hover:opacity-80"
          >
            <div class="flex items-center gap-2 min-w-0">
              <WifiOff class="w-3.5 h-3.5 text-status-critical shrink-0" />
              <span class="text-xs font-medium text-text-primary truncate">{{ d.name }}</span>
            </div>
            <span class="shrink-0 text-[10px] font-semibold text-status-critical">
              {{ d.consecutive_failures }} fail{{ d.consecutive_failures === 1 ? '' : 's' }}
            </span>
          </RouterLink>
        </div>
      </div>
    </div>

    <!-- Trend & distribution -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 bg-surface-raised p-5 rounded-xl border border-border shadow-sm">
        <h3 class="text-sm font-semibold text-text-primary mb-4">Configuration Drift Trend</h3>
        <div class="h-64">
          <Line v-if="!loading" :data="lineChartData" :options="lineChartOptions" />
          <div v-else class="h-full rounded-lg bg-surface-sunken animate-pulse" />
        </div>
      </div>

      <div class="bg-surface-raised p-5 rounded-xl border border-border shadow-sm">
        <h3 class="text-sm font-semibold text-text-primary mb-4">Severity Distribution</h3>
        <div class="h-64 flex items-center justify-center">
          <Doughnut v-if="!loading" :data="doughnutChartData" :options="doughnutChartOptions" />
          <div v-else class="h-full w-full rounded-lg bg-surface-sunken animate-pulse" />
        </div>
      </div>
    </div>

    <!-- Top devices by drift volume -->
    <div class="bg-surface-raised p-5 rounded-xl border border-border shadow-sm">
      <h3 class="text-sm font-semibold text-text-primary mb-1">Top Devices by Drift Volume</h3>
      <p class="text-xs text-text-secondary mb-4">Which devices generate the most config changes — a signal for instability or policy gaps</p>
      <div class="h-56">
        <Bar v-if="!loading && topDriftDevices.length > 0" :data="topDriftChartData" :options="topDriftChartOptions" />
        <div v-else-if="loading" class="h-full rounded-lg bg-surface-sunken animate-pulse" />
        <p v-else class="h-full flex items-center justify-center text-xs text-text-muted">No drift recorded yet.</p>
      </div>
    </div>
  </div>
</template>