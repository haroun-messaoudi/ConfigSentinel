import { apiClient } from '@/features/users/api/client'
import type { PaginatedResponse } from '@/types'
import type { Device, DeviceFormPayload, DeviceTypeOption } from '../types'

export const devicesApi = {
  async list(): Promise<Device[]> {
    const devices: Device[] = []
    let nextUrl: string | null = '/devices/'
    while (nextUrl) {
      const { data } = await apiClient.get<PaginatedResponse<Device> | Device[]>(nextUrl)
      if (Array.isArray(data)) return [...devices, ...data]
      devices.push(...data.results)
      nextUrl = data.next
    }
    return devices
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
