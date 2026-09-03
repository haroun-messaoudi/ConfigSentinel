import { apiClient } from '@/features/users/api/client'
import type { PaginatedResponse } from '@/types'
import type { Device, DeviceFormPayload, DeviceTypeOption } from '../types'

function unwrap<T>(data: PaginatedResponse<T> | T[]): T[] {
  return Array.isArray(data) ? data : data.results
}

export const devicesApi = {
  async list(): Promise<Device[]> {
    const { data } = await apiClient.get<PaginatedResponse<Device> | Device[]>('/devices/')
    return unwrap(data)
  },
  async get(id: number | string): Promise<Device> {
    const { data } = await apiClient.get<Device>(`/devices/${id}/`)
    return data
  },
  create(payload: DeviceFormPayload) {
    return apiClient.post<Device>('/devices/', payload)
  },
  update(id: number | string, payload: Partial<DeviceFormPayload>) {
    return apiClient.patch<Device>(`/devices/${id}/`, payload)
  },
  remove(id: number | string) {
    return apiClient.delete(`/devices/${id}/`)
  },
  checkNow(id: number | string) {
    return apiClient.post<{ status: string }>(`/devices/${id}/check_now/`)
  },
  pause(id: number | string) {
    return apiClient.post<Device>(`/devices/${id}/pause/`)
  },
  resume(id: number | string) {
    return apiClient.post<Device>(`/devices/${id}/resume/`)
  },
}
export const deviceTypesApi = {
  async list(): Promise<DeviceTypeOption[]> {
    const { data } = await apiClient.get<DeviceTypeOption[]>('/devices/types/')
    return data
  },
}
