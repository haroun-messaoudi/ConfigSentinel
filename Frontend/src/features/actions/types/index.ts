// --- Action Parameters ---

export interface ActionParameter {
  id?: number
  name: string
  label: string
  data_type: 'STRING' | 'INTEGER' | 'IP_ADDRESS' | 'BOOLEAN'
  is_required: boolean
  default_value?: string
  validation_regex?: string
}

export interface ActionParameterPayload {
  name: string
  label: string
  data_type: 'STRING' | 'INTEGER' | 'IP_ADDRESS' | 'BOOLEAN'
  is_required: boolean
  default_value?: string
  validation_regex?: string
}

// --- Action Templates ---

export interface ActionTemplate {
  id?: number
  device_type: string
  template_text: string
}

export interface ActionTemplatePayload {
  device_type: string
  template_text: string
}

// --- Action Definitions ---

export interface ActionDefinition {
  id: number
  name: string
  description: string
  created_by?: number
  created_at: string
  parameters: ActionParameter[]
  templates: ActionTemplate[]
}

export interface CreateActionDefinitionPayload {
  name: string
  description: string
  parameters?: ActionParameterPayload[]
  templates?: ActionTemplatePayload[]
}

// --- Device Permissions ---

export interface DevicePermission {
  id: number
  user: number
  user_username?: string
  device: number
  device_name?: string
  action_definition: number
  action_name?: string
  granted_by?: number
  granted_at?: string
}

// --- Change Requests ---

export interface ChangeRequestPayload {
  device: number
  action_definition: number
  params: Record<string, any>
}

export interface ChangeRequestItem {
  id: number
  action_definition: number
  action_name: string
  device: number
  device_name: string
  requested_by: number
  requested_by_username: string
  params: Record<string, any>
  status: 'PENDING' | 'SUCCESS' | 'FAILED'
  error_message?: string
  generated_commands: string
  requested_at: string
  applied_at?: string
}