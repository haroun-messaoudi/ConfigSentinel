import { apiClient } from '@/features/users/api/client'
import type { PaginatedResponse } from '@/types'
import type { ConfigChange } from '../types'

export const changesApi = {
  async list(filters?: { severity?: string; status?: string; device?: number | string }): Promise<ConfigChange[]> {
    const items: ConfigChange[] = []
    let nextUrl: string | null = '/changes/'
    let params: typeof filters = filters
    while (nextUrl) {
      const { data } = await apiClient.get<PaginatedResponse<ConfigChange> | ConfigChange[]>(nextUrl, { params })
      if (Array.isArray(data)) return [...items, ...data]
      items.push(...data.results)
      nextUrl = data.next
      params = undefined
    }
    return items
  },
  async get(id: number | string): Promise<ConfigChange> {
    const { data } = await apiClient.get<ConfigChange>(`/changes/${id}/`)
    return data
  },
  acknowledge(id: number | string) {
    return apiClient.post<ConfigChange>(`/changes/${id}/acknowledge/`)
  },
}