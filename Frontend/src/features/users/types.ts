export interface AppUser {
  id: number
  username: string
  email: string
  role: string | null
  is_active: boolean
  last_login: string | null
}

export interface UserFormPayload {
  username: string
  email: string
  role: string | null
  password: string
  is_active: boolean
}