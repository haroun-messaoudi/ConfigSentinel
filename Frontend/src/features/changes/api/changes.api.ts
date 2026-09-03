import { apiClient } from '@/features/users/api/client'
import type { PaginatedResponse } from '@/types'
import type { ConfigChange } from '../types'

function unwrap<T>(data: PaginatedResponse<T> | T[]): T[] {
  return Array.isArray(data) ? data : data.results
}

export const changesApi = {
  async list(filters?: { severity?: string; status?: string; device?: number | string }): Promise<ConfigChange[]> {
    const { data } = await apiClient.get<PaginatedResponse<ConfigChange> | ConfigChange[]>('/changes/', {
      params: filters,
    })
    return unwrap(data)
  },
  async get(id: number | string): Promise<ConfigChange> {
    const { data } = await apiClient.get<ConfigChange>(`/changes/${id}/`)
    return data
  },
  acknowledge(id: number | string) {
    return apiClient.post<ConfigChange>(`/changes/${id}/acknowledge/`)
  },
}