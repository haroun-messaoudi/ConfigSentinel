export interface SeverityClass {
  id: number
  name: string
  rank: number
}

export type TrackedConceptSource = 'BUILTIN' | 'CUSTOM'

export interface TrackedConcept {
  id: number
  name: string
  description: string
  pattern: string
  severity_class: number | null
  source: TrackedConceptSource
  created_by: number | null
}

export interface DetectionProfile {
  id: number
  name: string
  tracked_concepts: number[]
}