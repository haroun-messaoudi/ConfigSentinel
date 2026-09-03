import { apiClient } from '@/features/users/api/client'
import type { PaginatedResponse } from '@/types'
import type { DetectionProfile, TrackedConcept, SeverityClass } from '../types'

function unwrap<T>(data: PaginatedResponse<T> | T[]): T[] {
  return Array.isArray(data) ? data : data.results
}

export interface DetectionProfilePayload {
  name: string
  tracked_concepts: number[]
}

// Kept as `detectionApi` (unchanged shape for `.list()`) since DeviceFormModal
// already depends on it — extended here with the rest of profile CRUD.
export const detectionApi = {
  async list(): Promise<DetectionProfile[]> {
    const { data } = await apiClient.get<PaginatedResponse<DetectionProfile> | DetectionProfile[]>(
      '/detection-profiles/',
    )
    return unwrap(data)
  },
  create(payload: DetectionProfilePayload) {
    return apiClient.post<DetectionProfile>('/detection-profiles/', payload)
  },
  update(id: number, payload: Partial<DetectionProfilePayload>) {
    return apiClient.patch<DetectionProfile>(`/detection-profiles/${id}/`, payload)
  },
  remove(id: number) {
    return apiClient.delete(`/detection-profiles/${id}/`)
  },
}

export interface TrackedConceptPayload {
  name: string
  description: string
  pattern: string
  severity_class: number | null
}

export const trackedConceptsApi = {
  async list(): Promise<TrackedConcept[]> {
    const { data } = await apiClient.get<PaginatedResponse<TrackedConcept> | TrackedConcept[]>('/tracked-concepts/')
    return unwrap(data)
  },
  create(payload: TrackedConceptPayload) {
    return apiClient.post<TrackedConcept>('/tracked-concepts/', payload)
  },
  update(id: number, payload: Partial<TrackedConceptPayload>) {
    return apiClient.patch<TrackedConcept>(`/tracked-concepts/${id}/`, payload)
  },
  remove(id: number) {
    return apiClient.delete(`/tracked-concepts/${id}/`)
  },
}

export interface SeverityClassPayload {
  name: string
  rank: number
}

export const severityClassesApi = {
  async list(): Promise<SeverityClass[]> {
    const { data } = await apiClient.get<PaginatedResponse<SeverityClass> | SeverityClass[]>('/severity-classes/')
    return unwrap(data)
  },
  create(payload: SeverityClassPayload) {
    return apiClient.post<SeverityClass>('/severity-classes/', payload)
  },
  update(id: number, payload: Partial<SeverityClassPayload>) {
    return apiClient.patch<SeverityClass>(`/severity-classes/${id}/`, payload)
  },
  remove(id: number) {
    return apiClient.delete(`/severity-classes/${id}/`)
  },
}