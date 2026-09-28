import { actionsApi } from '@/features/actions/api/actions.api'
import { changesApi } from '@/features/changes/api/changes.api'
import type { ConfigChange } from '@/features/changes/types'

export async function getOperatorDeviceIds(): Promise<Set<number>> {
  const permissions = await actionsApi.listPermissions()
  return new Set(permissions.map((permission) => permission.device))
}

export async function listChangesForDevices(
  deviceIds: Iterable<number>,
  filters?: { status?: string },
): Promise<ConfigChange[]> {
  const changes = await Promise.all(
    Array.from(deviceIds, (device) => changesApi.list({ ...filters, device })),
  )
  return changes.flat().sort((a, b) => new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime())
}