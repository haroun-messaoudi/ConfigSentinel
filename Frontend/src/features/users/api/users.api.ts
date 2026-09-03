import { apiClient } from './client'
import type { PaginatedResponse } from '@/types'
import type { AppUser, UserFormPayload } from '../types'

function unwrap<T>(data: PaginatedResponse<T> | T[]): T[] {
  return Array.isArray(data) ? data : data.results
}

export interface ChangePasswordPayload {
  old_password: string
  new_password: string
}

export const usersApi = {
  async list(): Promise<AppUser[]> {
    const { data } = await apiClient.get<PaginatedResponse<AppUser> | AppUser[]>('/users/')
    return unwrap(data)
  },
  create(payload: UserFormPayload) {
    return apiClient.post<AppUser>('/users/', payload)
  },
  update(id: number, payload: Partial<UserFormPayload>) {
    return apiClient.patch<AppUser>(`/users/${id}/`, payload)
  },
  changePassword(payload: ChangePasswordPayload) {
    return apiClient.post<{ status: string }>('/change-password/', payload)
  },
}