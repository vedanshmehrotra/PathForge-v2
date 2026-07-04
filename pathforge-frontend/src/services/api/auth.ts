import { apiRequest } from './client'
import type { UserProfile, AuthProfile } from '@/types/api'

export function fetchMe(): Promise<UserProfile> {
  return apiRequest<UserProfile>('/auth/me')
}

export function fetchAuthProfile(): Promise<AuthProfile> {
  return apiRequest<AuthProfile>('/auth/profile')
}
