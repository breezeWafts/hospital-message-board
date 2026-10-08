/** 秘书 API */
import type {
  Department,
  MessageDetail,
  MessageListItem,
  PageResult,
  TaskDetail,
  TaskListItem,
} from '@/types'
import { http } from './http'

export interface MessageListParams {
  status?: string
  search?: string
  page?: number
  page_size?: number
  sort?: string
}

/** GET /api/secretary/messages */
export function listMessages(params: MessageListParams) {
  return http.get<PageResult<MessageListItem>>('/secretary/messages', { params })
}

/** GET /api/secretary/messages/{id} */
export function getMessage(id: number) {
  return http.get<MessageDetail>(`/secretary/messages/${id}`)
}

/** POST /api/secretary/messages/{id}/review —— 驳回/拒绝必须填写 comment */
export function reviewMessage(id: number, result: 'APPROVED' | 'REJECTED' | 'REFUSED', comment?: string) {
  return http.post<MessageDetail>(`/secretary/messages/${id}/review`, { result, comment })
}

export interface TaskAssignItem {
  department_id: number
  title: string
  content?: string
}

/** POST /api/secretary/messages/{id}/tasks/assign */
export function assignTasks(messageId: number, tasks: TaskAssignItem[]) {
  return http.post<{ id: number; status: string; task_ids: number[]; task_count: number }>(
    `/secretary/messages/${messageId}/tasks/assign`,
    { tasks },
  )
}

/** GET /api/secretary/tasks */
export function listTasks(params: { status?: string; message_id?: number; page?: number; page_size?: number; sort?: string }) {
  return http.get<PageResult<TaskListItem>>('/secretary/tasks', { params })
}

/** GET /api/secretary/tasks/{task_id} */
export function getTask(taskId: number) {
  return http.get<TaskDetail>(`/secretary/tasks/${taskId}`)
}

/** POST /api/secretary/tasks/{task_id}/review —— 驳回必须填写 comment */
export function reviewTask(taskId: number, result: 'APPROVED' | 'REJECTED', comment?: string) {
  return http.post<TaskDetail>(`/secretary/tasks/${taskId}/review`, { result, comment })
}

/** POST /api/secretary/messages/{id}/archive */
export function archiveMessage(id: number) {
  return http.post<MessageDetail>(`/secretary/messages/${id}/archive`)
}

/** GET /api/secretary/departments —— 启用中的部门（分派任务下拉用） */
export function listDepartments() {
  return http.get<Department[]>('/secretary/departments')
}
