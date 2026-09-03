import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { registerRefreshHandlers } from '@/features/users/api/client'
import { authApi } from '../api'
import type { LoginCredentials } from '../types'
import type { UserRole } from '@/types'

interface SessionUser {
  id: number
  username: string
  role: UserRole | null
}

function normalizeRole(role: string | null): UserRole | null {
  if (!role) return null
  return role.toLowerCase() as UserRole
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<SessionUser | null>(null)
  const isReady = ref(false)

  const isAuthenticated = computed(() => user.value !== null)
  const role = computed<UserRole | null>(() => user.value?.role ?? null)

  let restorePromise: Promise<void> | null = null

  function hasRole(...roles: UserRole[]) {
    return role.value !== null && roles.includes(role.value)
  }

  function clearSession() {
    user.value = null
  }

  function forceLogout() {
    clearSession()
    window.location.href = '/login'
  }

  async function fetchCurrentUser() {
    const me = await authApi.me()
    user.value = { id: me.id, username: me.username, role: normalizeRole(me.role) }
  }

  async function login(credentials: LoginCredentials) {
    await authApi.login(credentials)
    await fetchCurrentUser()
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch {
    } finally {
      clearSession()
      window.location.href = '/login'
    }
  }

  // Used exclusively by the Axios client interceptor when a 401 occurs
  async function refreshAccessToken(): Promise<boolean> {
    try {
      await authApi.refresh()
      return true
    } catch {
      return false
    }
  }

  async function restoreSession() {
    if (isReady.value) return
    if (restorePromise) return restorePromise

    restorePromise = (async () => {
      try {
        // If the access token cookie is valid or can be auto-refreshed by 
        // the interceptor on failure, fetchCurrentUser will succeed.
        await fetchCurrentUser()
      } catch {
        clearSession()
      } finally {
        isReady.value = true
      }
    })()

    try {
      await restorePromise
    } finally {
      restorePromise = null
    }
  }

  // Register handlers so client.ts handles 401 retries & forced logouts cleanly
  registerRefreshHandlers(refreshAccessToken, forceLogout)

  return {
    user,
    isAuthenticated,
    isReady,
    role,
    hasRole,
    login,
    logout,
    restoreSession,
  }
})