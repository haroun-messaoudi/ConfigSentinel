import { apiClient } from '@/features/users/api/client'
import type { PaginatedResponse } from '@/types'
import type { Alert } from '../types'

function unwrap<T>(data: PaginatedResponse<T> | T[]): T[] {
  return Array.isArray(data) ? data : data.results
}

export const alertsApi = {
  async list(delivered?: boolean): Promise<Alert[]> {
    const params = delivered === undefined ? {} : { delivered: String(delivered) }
    const { data } = await apiClient.get<PaginatedResponse<Alert> | Alert[]>('/alerts/', { params })
    return unwrap(data)
  },
  markDelivered(id: number) {
    return apiClient.post<Alert>(`/alerts/${id}/mark_delivered/`)
  },
}