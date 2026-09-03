import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type { ApiError } from '@/types'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true, // Required for HttpOnly cookies
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
})

let refreshPromise: Promise<boolean> | null = null
let onRefreshFailed: (() => void) | null = null
let refreshInvoker: (() => Promise<boolean>) | null = null

export function registerRefreshHandlers(refresh: () => Promise<boolean>, onFail: () => void) {
  refreshInvoker = refresh
  onRefreshFailed = onFail
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined
    const url = original?.url || ''
    
    const isAuthEndpoint = url.includes('token') || url.includes('logout') || url.includes('me') || url.includes('login')

    if (error.response?.status === 401 && original && !original._retry && !isAuthEndpoint && refreshInvoker) {
      original._retry = true
      
      refreshPromise ??= refreshInvoker().finally(() => {
        refreshPromise = null
      })

      const refreshed = await refreshPromise
      
      if (refreshed) {
        // Re-dispatch the exact original request (whether GET, POST, PUT, etc.)
        return apiClient(original)
      }
      
      onRefreshFailed?.()
    }

    return Promise.reject(normalizeError(error))
  },
)

function normalizeError(error: AxiosError): ApiError {
  const status = error.response?.status ?? 0
  const data = error.response?.data as Record<string, unknown> | undefined

  if (data && typeof data === 'object' && 'detail' in data) {
    return { status, message: String(data.detail) }
  }
  if (data && typeof data === 'object') {
    const fieldErrors = data as Record<string, string[]>
    return { status, message: 'Validation failed', fieldErrors }
  }
  return { status, message: error.message || 'Network error' }
}