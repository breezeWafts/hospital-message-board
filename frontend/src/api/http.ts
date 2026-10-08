/**
 * axios 统一封装：
 * - baseURL=/api（开发环境由 Vite 代理到 http://localhost:8000，生产由 Nginx 反代）
 * - 自动附加 Authorization: Bearer <token>
 * - 统一错误提示（ElMessage），detail 兼容字符串 / 对象 / 422 数组
 * - 401 自动清理会话并跳转登录
 */
import axios, { AxiosError } from 'axios'
import { ElMessage } from 'element-plus'

import { formatDateTime } from '@/utils/format'

declare module 'axios' {
  export interface AxiosRequestConfig {
    /** 为 true 时该请求失败不弹全局错误提示（页面自行处理） */
    silent?: boolean
  }
}

export const TOKEN_KEY = 'hmb_token'
export const USER_KEY = 'hmb_user'

export const http = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export interface ApiErrorInfo {
  status?: number
  message: string
  attemptsLeft?: number | null
  lockedUntil?: string | null
}

/** 从任意异常中提取可读错误信息（兼容 FastAPI 的 detail 字符串/对象/数组） */
export function extractApiError(e: unknown): ApiErrorInfo {
  const err = e as AxiosError<{ detail?: unknown }>
  const status = err?.response?.status
  let detail: unknown = err?.response?.data?.detail
  let message = ''
  let attemptsLeft: number | null = null
  let lockedUntil: string | null = null

  if (typeof detail === 'string') {
    message = detail
  } else if (Array.isArray(detail)) {
    message = detail
      .map((d) => {
        if (typeof d === 'string') return d
        if (d && typeof d === 'object') {
          const item = d as { msg?: string; loc?: unknown[] }
          const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : undefined
          return item.msg ? `${item.msg}${field ? `（${String(field)}）` : ''}` : '参数错误'
        }
        return '参数错误'
      })
      .join('；')
  } else if (detail && typeof detail === 'object') {
    const obj = detail as { message?: string; attempts_left?: number; locked_until?: string }
    message = obj.message || '请求失败'
    attemptsLeft = typeof obj.attempts_left === 'number' ? obj.attempts_left : null
    lockedUntil = obj.locked_until || null
  }

  if (!message) {
    if (status === 401) message = '未登录或登录已失效'
    else if (status === 403) message = '无权访问该资源'
    else if (status === 404) message = '资源不存在'
    else if (status === 423) message = '已锁定'
    else if (status === 429) message = '操作过于频繁，请稍后再试'
    else if (status && status >= 500) message = '服务器内部错误，请稍后再试'
    else if (err?.code === 'ECONNABORTED') message = '请求超时，请稍后再试'
    else message = '网络错误，请检查网络连接'
  }

  if (status === 423 && lockedUntil) {
    message = `${message}（解锁时间：${formatDateTime(lockedUntil)}）`
  }
  if (attemptsLeft !== null) {
    message = `${message}（剩余尝试次数：${attemptsLeft}）`
  }
  return { status, message, attemptsLeft, lockedUntil }
}

/** 当前请求是否携带了认证头（用于区分匿名/登录态请求） */
function isAuthRequest(config?: unknown): boolean {
  const headers = (config as { headers?: Record<string, unknown> } | undefined)?.headers
  const auth = headers?.['Authorization'] ?? headers?.['authorization']
  return typeof auth === 'string' && auth.length > 0
}

async function redirectToLogin() {
  const { default: router } = await import('@/router')
  const current = router.currentRoute.value
  if (current.path !== '/login') {
    router.push({ name: 'login', query: { redirect: current.fullPath } })
  }
}

http.interceptors.response.use(
  (res) => res,
  (error: AxiosError) => {
    const info = extractApiError(error)
    if (info.status === 401 && isAuthRequest(error.config)) {
      // 登录态失效：清理本地会话并跳转登录
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
      ElMessage.error('登录已失效，请重新登录')
      void redirectToLogin()
    } else if (!(error.config as { silent?: boolean } | undefined)?.silent) {
      ElMessage.error(info.message)
    }
    return Promise.reject(error)
  },
)

/**
 * 附件下载：全部走后端鉴权接口。对登录用户必须带 Authorization 头，
 * 因此统一用 axios 拉取 blob 再触发浏览器下载；匿名附件 URL 已含 anon_token。
 */
export async function downloadAttachment(
  item: { download_url: string; original_name: string },
  options: { silent?: boolean } = {},
): Promise<void> {
  // download_url 形如 "/api/attachments/..."，去除前缀后拼到 baseURL=/api 上，避免双 /api
  const url = item.download_url.replace(/^\/api/, '')
  const res = await http.get(url, { responseType: 'blob', silent: options.silent, timeout: 60000 })
  const blob = new Blob([res.data as BlobPart])
  const objectUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objectUrl
  a.download = item.original_name
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 5000)
}
