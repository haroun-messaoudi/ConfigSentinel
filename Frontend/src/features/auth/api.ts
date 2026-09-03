import { apiClient } from '@/features/users/api/client'
import type { LoginCredentials } from './types'
import type { AppUser } from '@/features/users/types'

export const authApi = {
  login(credentials: LoginCredentials) {
    return apiClient.post('/token/', credentials).then(() => undefined)
  },
  refresh() {
    return apiClient.post('/token/refresh/').then(() => undefined)
  },
  logout() {
    return apiClient.post('/logout/').then(() => undefined)
  },
  me() {
    return apiClient.get<AppUser>('/me/').then((r) => r.data)
  },
}