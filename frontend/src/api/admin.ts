/** 管理员 API：用户/部门/配置/日志/验证码重置/IP 黑名单 */
import type {
  AuditLog,
  BlacklistItem,
  Department,
  PageResult,
  User,
} from '@/types'
import { http } from './http'

// ---------------- 用户 ----------------

export function listUsers(params: { search?: string; page?: number; page_size?: number }) {
  return http.get<PageResult<User>>('/admin/users', { params })
}

export interface UserCreatePayload {
  username: string
  password?: string
  display_name?: string
  phone?: string
  email?: string
  role?: string | null
  department_id?: number | null
  is_active?: boolean
}

export function createUser(payload: UserCreatePayload) {
  return http.post<User>('/admin/users', payload)
}

export interface UserUpdatePayload {
  display_name?: string
  phone?: string
  email?: string
  role?: string | null
  department_id?: number | null
  is_active?: boolean
  password?: string
}

export function updateUser(userId: number, payload: UserUpdatePayload) {
  return http.patch<User>(`/admin/users/${userId}`, payload)
}

// ---------------- 部门 ----------------

export function listDepartments() {
  return http.get<Department[]>('/admin/departments')
}

export function createDepartment(payload: { name: string; code: string }) {
  return http.post<Department>('/admin/departments', payload)
}

export function updateDepartment(deptId: number, payload: { name?: string; is_active?: boolean }) {
  return http.patch<Department>(`/admin/departments/${deptId}`, payload)
}

// ---------------- 系统配置 ----------------

export function getConfigs() {
  return http.get<{ configs: Record<string, string> }>('/admin/configs')
}

export function updateConfigs(configs: Record<string, string>) {
  return http.put<{ configs: Record<string, string> }>('/admin/configs', { configs })
}

// ---------------- 验证码重置 ----------------

export function resetCaptcha(messageId: number) {
  return http.post<{ ok: boolean; message_id: number }>('/admin/messages/reset-captcha', { message_id: messageId })
}

// ---------------- 日志 ----------------

export interface LogQueryParams {
  action?: string
  operator?: string
  role?: string
  message_id?: number
  task_id?: number
  date_from?: string
  date_to?: string
  sort?: string
  page?: number
  page_size?: number
}

export function listLogs(params: LogQueryParams) {
  return http.get<PageResult<AuditLog>>('/admin/logs', { params })
}

// ---------------- IP 黑名单 ----------------

export function listBlacklist() {
  return http.get<{ items: BlacklistItem[] }>('/admin/blacklist')
}

export function removeBlacklist(ip: string) {
  return http.delete<{ ok: boolean }>(`/admin/blacklist/${encodeURIComponent(ip)}`)
}
