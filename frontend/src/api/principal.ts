/** 院长 API */
import type { MessageDetail, MessageListItem, PageResult, TaskDetail } from '@/types'
import { http } from './http'

export interface MessageListParams {
  status?: string
  view?: 'instruction' | 'confirm' | 'all'
  search?: string
  page?: number
  page_size?: number
  sort?: string
}

/** GET /api/principal/messages */
export function listMessages(params: MessageListParams) {
  return http.get<PageResult<MessageListItem>>('/principal/messages', { params })
}

/** GET /api/principal/messages/{id} */
export function getMessage(id: number) {
  return http.get<MessageDetail>(`/principal/messages/${id}`)
}

/** POST /api/principal/messages/{id}/instruction */
export function submitInstruction(id: number, instruction: string) {
  return http.post<MessageDetail>(`/principal/messages/${id}/instruction`, { instruction })
}

/** POST /api/principal/messages/{id}/confirm */
export function confirmMessage(id: number) {
  return http.post<MessageDetail>(`/principal/messages/${id}/confirm`)
}

/** POST /api/principal/messages/{id}/reject */
export function rejectMessage(id: number, comment: string) {
  return http.post<MessageDetail>(`/principal/messages/${id}/reject`, { comment })
}

/** GET /api/principal/tasks/{task_id} */
export function getTask(taskId: number) {
  return http.get<TaskDetail>(`/principal/tasks/${taskId}`)
}
