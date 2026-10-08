/** 全局数据类型：与后端 app/schemas.py、app/services/*.py 序列化结果一一对应 */

export type Role = 'admin' | 'principal' | 'secretary' | 'department' | 'anonymous' | 'system'

export type MessageStatus = 'NEW' | 'PENDING' | 'REVIEWING' | 'COMPLETED' | 'REJECTED' | 'ARCHIVED'

export type TaskStatus = 'PENDING' | 'REVIEWING' | 'APPROVED'

export type ReviewResult = 'APPROVED' | 'REJECTED' | 'REFUSED'

export interface User {
  id: number
  username: string
  display_name?: string | null
  phone?: string | null
  email?: string | null
  auth_source?: string
  role?: Role | string | null
  department_id?: number | null
  department_name?: string | null
  is_active?: boolean
  must_change_password?: boolean
}

export interface LoginResult {
  token: string
  user: User
}

export interface PageResult<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}

export interface Attachment {
  id: number
  original_name: string
  size_bytes: number
  mime_type: string
  created_at: string
  /** 相对路径下载地址（匿名场景已附带 anon_token 查询参数） */
  download_url: string
}

export interface Review {
  id?: number
  result: ReviewResult
  comment?: string | null
  created_at: string
  reviewer_name: string
  role: string
}

export interface Task {
  id: number
  message_id: number
  department_id: number
  department_name: string
  assigner_name: string
  title: string
  content?: string | null
  processing_content?: string | null
  status: TaskStatus
  last_review_result?: ReviewResult | null
  last_review_comment?: string | null
  submitted_at?: string | null
  approved_at?: string | null
  created_at: string
  updated_at?: string
  attachments: Attachment[]
  reviews: Review[]
}

export interface WorkflowStage {
  key: string
  label: string
  reached: boolean
  at?: string | null
}

export interface WorkflowLoop {
  task_id: number
  department?: string | null
  at: string
  comment?: string | null
}

export interface Workflow {
  current: string
  stages: WorkflowStage[]
  loops: WorkflowLoop[]
}

export interface MessageListItem {
  id: number
  title: string
  status: MessageStatus
  created_at: string
  updated_at?: string | null
  completed_at?: string | null
  archived_at?: string | null
  evaluation_satisfied?: boolean | null
  principal_instruction?: string | null
  secretary_review_result?: ReviewResult | null
  secretary_review_comment?: string | null
  secretary_reviewed_at?: string | null
  captcha_expires_at?: string | null
  task_count?: number
  department_names?: string | null
}

export interface Evaluation {
  satisfied: boolean
  content?: string | null
  created_at: string
}

export interface MessageDetail extends MessageListItem {
  content?: string
  attachments?: Attachment[]
  tasks: Task[]
  reviews: Review[]
  workflow: Workflow
  can_evaluate: boolean
  /** 秘书/管理员可见 */
  submit_ip?: string | null
  submit_ua?: string | null
  captcha_attempts?: number | null
  captcha_locked_until?: string | null
  secretary_reviewer_name?: string | null
  evaluations?: Evaluation[]
}

/** 匿名查询未完成留言时返回的基础信息 */
export interface AnonymousBasicResult {
  id: number
  title: string
  status: MessageStatus
  created_at: string
  updated_at?: string | null
  captcha_expires_at?: string | null
}

export interface AnonymousSubmitResult {
  id: number
  captcha: string
  message: string
}

export interface TaskListItem {
  id: number
  message_id: number
  message_title: string
  message_status: MessageStatus
  department_id: number
  department_name: string
  title: string
  content?: string | null
  processing_content?: string | null
  status: TaskStatus
  last_review_result?: ReviewResult | null
  submitted_at?: string | null
  approved_at?: string | null
  created_at: string
  updated_at?: string
}

export interface TaskDetail extends TaskListItem {
  assigner_name: string
  last_review_comment?: string | null
  attachments: Attachment[]
  reviews: Review[]
}

export interface Department {
  id: number
  name: string
  code: string
  is_active: boolean
  created_at?: string
  updated_at?: string
}

export interface AuditLog {
  id: number
  operator_id?: number | null
  operator_name?: string | null
  role?: string | null
  ip?: string | null
  ua?: string | null
  action: string
  before_status?: string | null
  after_status?: string | null
  message_id?: number | null
  task_id?: number | null
  created_at: string
}

export interface BlacklistItem {
  id: number
  ip: string
  reason?: string | null
  created_at: string
  expires_at?: string | null
}

/** 本地账号登录表单 */
export interface LoginForm {
  username: string
  password: string
}

/** 修改密码 */
export interface ChangePasswordForm {
  old_password: string
  new_password: string
}
