import { apiClient } from '@/features/users/api/client'
import type { PaginatedResponse } from '@/types'
import type {
  ActionDefinition,
  ActionTemplate,
  DevicePermission,
  ChangeRequestPayload,
  ChangeRequestItem,
  CreateActionDefinitionPayload
} from '../types'

export interface ChoiceOption {
  value: string
  label: string
}

export interface ActionChoicesResponse {
  data_types: ChoiceOption[]
}

function unwrap<T>(data: PaginatedResponse<T> | T[]): T[] {
  return Array.isArray(data) ? data : data.results
}

async function fetchAllPages<T>(url: string, params?: Record<string, number>): Promise<T[]> {
  const items: T[] = []
  let nextUrl: string | null = url
  let nextParams = params

  while (nextUrl) {
    const { data } = await apiClient.get<PaginatedResponse<T> | T[]>(nextUrl, { params: nextParams })
    if (Array.isArray(data)) return [...items, ...data]
    items.push(...data.results)
    nextUrl = data.next
    nextParams = undefined
  }

  return items
}

export const actionsApi = {
  async listDefinitions(): Promise<ActionDefinition[]> {
    const { data } = await apiClient.get<PaginatedResponse<ActionDefinition> | ActionDefinition[]>('/action-definitions/')
    return unwrap(data)
  },

  createDefinition(payload: CreateActionDefinitionPayload) {
    return apiClient.post<ActionDefinition>('/action-definitions/', payload)
  },

  async listTemplates(actionDefinitionId?: number): Promise<ActionTemplate[]> {
    const { data } = await apiClient.get<PaginatedResponse<ActionTemplate> | ActionTemplate[]>(
      '/action-templates/',
      actionDefinitionId ? { params: { action_definition: actionDefinitionId } } : undefined,
    )
    return unwrap(data)
  },

  createTemplate(payload: { action_definition: number; device_type: string; template_text: string }) {
    return apiClient.post<ActionTemplate>('/action-templates/', payload)
  },

  async listPermissions(params?: { user?: number; device?: number }): Promise<DevicePermission[]> {
    return fetchAllPages<DevicePermission>('/device-permissions/', params)
  },

  assignPermission(payload: { user: number; device: number; action_definition: number }) {
    return apiClient.post<DevicePermission>('/device-permissions/', payload)
  },

  revokePermission(id: number) {
    return apiClient.delete(`/device-permissions/${id}/`)
  },

  async listChangeRequests(): Promise<ChangeRequestItem[]> {
    return fetchAllPages<ChangeRequestItem>('/change-requests/')
  },

  async getChangeRequest(id: number): Promise<ChangeRequestItem> {
    const { data } = await apiClient.get<ChangeRequestItem>(`/change-requests/${id}/`)
    return data
  },

  submitChangeRequest(payload: ChangeRequestPayload) {
    return apiClient.post<ChangeRequestItem>('/change-requests/', payload)
  },

  confirmChangeRequest(id: number) {
    return apiClient.post<{ detail: string }>(`/change-requests/${id}/confirm/`)
  },

  async getChoices(): Promise<ActionChoicesResponse> {
    const { data } = await apiClient.get<ActionChoicesResponse>('/action-choices/')
    return data
  },
}