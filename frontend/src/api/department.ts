/** 部门端 API */
import type { PageResult, TaskDetail, TaskListItem } from '@/types'
import { http } from './http'

/** GET /api/department/tasks —— 仅本部门任务 */
export function listTasks(params: { status?: string; page?: number; page_size?: number; sort?: string }) {
  return http.get<PageResult<TaskListItem>>('/department/tasks', { params })
}

/** GET /api/department/tasks/{task_id} */
export function getTask(taskId: number) {
  return http.get<TaskDetail>(`/department/tasks/${taskId}`)
}

/** POST /api/department/tasks/{task_id}/submit —— multipart: content, attachments */
export function submitTask(
  taskId: number,
  form: FormData,
  onProgress?: (percent: number) => void,
) {
  return http.post<TaskDetail>(`/department/tasks/${taskId}/submit`, form, {
    timeout: 180000,
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    },
  })
}
