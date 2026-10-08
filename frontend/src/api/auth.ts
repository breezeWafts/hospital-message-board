/** 认证相关 API */
import type { ChangePasswordForm, LoginResult, User } from '@/types'
import { http } from './http'

/** POST /api/auth/login */
export function login(username: string, password: string) {
  return http.post<LoginResult>('/auth/login', { username, password })
}

/** POST /api/auth/change-password */
export function changePassword(data: ChangePasswordForm) {
  return http.post<{ ok: boolean }>('/auth/change-password', data)
}

/** GET /api/auth/me */
export function me() {
  return http.get<User>('/auth/me')
}

/** GET /api/auth/oauth2/login —— 统一认证登录入口（后端 302 到认证中心） */
export const OAUTH_LOGIN_URL = '/api/auth/oauth2/login'
