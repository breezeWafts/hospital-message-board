/** 匿名端 API：提交留言（multipart）、查询、评价 */
import type {
  AnonymousBasicResult,
  AnonymousSubmitResult,
  MessageDetail,
} from '@/types'
import { http } from './http'

/** POST /api/anonymous/messages —— multipart: title, content, attachments */
export function submitMessage(form: FormData, onProgress?: (percent: number) => void) {
  return http.post<AnonymousSubmitResult>('/anonymous/messages', form, {
    timeout: 180000,
    silent: true,
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    },
  })
}

/** POST /api/anonymous/messages/query —— 返回基础信息或完整详情（COMPLETED/ARCHIVED） */
export function queryMessage(id: number, captcha: string) {
  return http.post<AnonymousBasicResult | MessageDetail>('/anonymous/messages/query', { id, captcha }, { silent: true })
}

/** POST /api/anonymous/messages/{id}/evaluate */
export function evaluateMessage(id: number, captcha: string, satisfied: boolean, content?: string) {
  return http.post<MessageDetail>(`/anonymous/messages/${id}/evaluate`, { captcha, satisfied, content }, { silent: true })
}
