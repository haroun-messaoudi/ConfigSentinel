import { ref } from 'vue'
import { alertsApi } from '@/features/alerts/api/alerts.api'
import { changesApi } from '@/features/changes/api/changes.api'

const undeliveredAlerts = ref(0)
const flaggedChanges = ref(0)
let pollStarted = false

async function refreshCounts() {
  try {
    const [alerts, changes] = await Promise.all([
      alertsApi.list(false),
      changesApi.list({ status: 'FLAGGED' }),
    ])
    undeliveredAlerts.value = alerts.length
    flaggedChanges.value = changes.length
  } catch {
    // silent — badges just skip this refresh cycle, not worth surfacing an error for
  }
}

export function useNotificationCounts() {
  if (!pollStarted) {
    pollStarted = true
    refreshCounts()
    setInterval(refreshCounts, 30000)
  }
  return { undeliveredAlerts, flaggedChanges, refreshCounts }
}