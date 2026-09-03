export interface Snapshot {
  id: number
  device: number
  taken_at: string
  raw_text: string
  config_hash: string
  is_baseline: boolean
}