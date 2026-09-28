import { ref } from 'vue'
import { useAuthStore } from '@/features/auth/stores/auth.store'
import { alertsApi } from '@/features/alerts/api/alerts.api'
import { changesApi } from '@/features/changes/api/changes.api'
import { getOperatorDeviceIds, listChangesForDevices } from '@/utils/operatorScope'

const undeliveredAlerts = ref(0)
const flaggedChanges = ref(0)
let pollStarted = false

async function refreshCounts() {
  try {
    const auth = useAuthStore()
    if (auth.hasRole('operator')) {
      const deviceIds = await getOperatorDeviceIds()
      const changes = await listChangesForDevices(deviceIds, { status: 'FLAGGED' })
      undeliveredAlerts.value = 0
      flaggedChanges.value = changes.length
    } else {
      const [alerts, changes] = await Promise.all([
        alertsApi.list(false),
        changesApi.list({ status: 'FLAGGED' }),
      ])
      undeliveredAlerts.value = alerts.length
      flaggedChanges.value = changes.length
    }
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