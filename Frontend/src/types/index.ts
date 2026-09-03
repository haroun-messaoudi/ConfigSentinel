// Global, cross-feature types.
// Feature-specific types (Device, ConfigChange, Alert, ...) live in
// src/features/<feature>/types/ instead of here — keep this file for
// things genuinely shared across the whole app.

export type UserRole = 'admin' | 'operator' | 'viewer'

export interface User {
  id: number
  username: string
  role: UserRole
}

/** Shape returned by DRF's default PageNumberPagination. */
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

/** Normalized shape we coerce every API error into (see api/client.ts). */
export interface ApiError {
  status: number
  message: string
  fieldErrors?: Record<string, string[]>
}
