import { apiClient } from '@/features/users/api/client'
import type { PaginatedResponse } from '@/types'
import type { Snapshot } from '../types'

function unwrap<T>(data: PaginatedResponse<T> | T[]): T[] {
  return Array.isArray(data) ? data : data.results
}

export const snapshotsApi = {
  async listForDevice(deviceId: number | string): Promise<Snapshot[]> {
    const { data } = await apiClient.get<PaginatedResponse<Snapshot> | Snapshot[]>('/snapshots/', {
      params: { device: deviceId },
    })
    return unwrap(data)
  },
  setBaseline(id: number) {
    return apiClient.post<Snapshot>(`/snapshots/${id}/set_baseline/`)
  },
}