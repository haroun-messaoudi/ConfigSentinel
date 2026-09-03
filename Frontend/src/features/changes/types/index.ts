export type ChangeStatus = 'FLAGGED' | 'INFORMATIONAL' | 'ACKNOWLEDGED'

export interface ConfigChange {
  id: number
  device: number
  device_name: string
  old_snapshot: number
  new_snapshot: number
  diff_text: string
  severity_class: number | null
  severity_name: string | null
  matched_concepts: number[]
  matched_concept_names: string[]
  detected_at: string
  status: ChangeStatus
  acknowledged_at: string | null
  acknowledged_by: number | null
  acknowledged_by_username: string | null
}