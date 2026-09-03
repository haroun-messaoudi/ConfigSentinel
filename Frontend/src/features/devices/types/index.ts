export type DeviceType = string // now backend-driven; see deviceTypesApi

export interface DeviceTypeOption {
  value: string
  label: string
}

export type PollStatus = 'OK' | 'ERROR' | null

export interface Device {
  id: number
  name: string
  hostname: string
  management_ip: string
  port: number
  device_type: DeviceType
  username: string
  poll_interval_minutes: number
  detection_profile: number | null
  is_active: boolean
  last_poll_status: PollStatus
  last_poll_error: string | null
  last_polled_at: string | null
  consecutive_failures: number
}

export interface DeviceFormPayload {
  name: string
  hostname: string
  management_ip: string
  port: number
  device_type: DeviceType
  username: string
  password?: string
  enable_secret?: string
  poll_interval_minutes: number
  detection_profile: number | null
}