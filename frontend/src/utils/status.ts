/** 状态/角色/审核结果/审计动作 的文案与标签类型映射（与后端 constants.py 一致） */

export type TagType = 'primary' | 'success' | 'info' | 'warning' | 'danger' | ''

export const MESSAGE_STATUS_TEXT: Record<string, string> = {
  NEW: '待秘书审核',
  PENDING: '部门处理中',
  REVIEWING: '待复核/待院长确认',
  COMPLETED: '已完成',
  REJECTED: '已驳回',
  ARCHIVED: '已归档',
}

export const TASK_STATUS_TEXT: Record<string, string> = {
  PENDING: '待处理',
  REVIEWING: '待秘书审核',
  APPROVED: '已通过',
}

export const REVIEW_RESULT_TEXT: Record<string, string> = {
  APPROVED: '通过',
  REJECTED: '驳回',
  REFUSED: '拒绝',
}

export const ROLE_TEXT: Record<string, string> = {
  admin: '系统管理员',
  principal: '院长',
  secretary: '秘书',
  department: '部门负责人',
  anonymous: '匿名用户',
  system: '系统',
}

export function messageStatusText(status?: string | null): string {
  return (status && MESSAGE_STATUS_TEXT[status]) || status || '—'
}

export function taskStatusText(status?: string | null): string {
  return (status && TASK_STATUS_TEXT[status]) || status || '—'
}

export function reviewResultText(result?: string | null): string {
  return (result && REVIEW_RESULT_TEXT[result]) || result || '—'
}

export function roleText(role?: string | null): string {
  return (role && ROLE_TEXT[role]) || role || '未授权'
}

export function messageStatusType(status?: string | null): TagType {
  switch (status) {
    case 'COMPLETED':
    case 'ARCHIVED':
      return 'success'
    case 'REJECTED':
      return 'danger'
    case 'NEW':
      return 'warning'
    case 'PENDING':
    case 'REVIEWING':
      return 'primary'
    default:
      return 'info'
  }
}

export function taskStatusType(status?: string | null): TagType {
  switch (status) {
    case 'APPROVED':
      return 'success'
    case 'PENDING':
      return 'warning'
    case 'REVIEWING':
      return 'primary'
    default:
      return 'info'
  }
}

export function reviewResultType(result?: string | null): TagType {
  switch (result) {
    case 'APPROVED':
      return 'success'
    case 'REJECTED':
    case 'REFUSED':
      return 'danger'
    default:
      return 'info'
  }
}

/** 审计动作列表（后端 AuditAction） */
export const AUDIT_ACTIONS: string[] = [
  'LOGIN_SUCCESS',
  'LOGIN_FAILED',
  'PASSWORD_CHANGED',
  'OAUTH_LOGIN',
  'ANON_SUBMIT',
  'ANON_QUERY',
  'ANON_QUERY_FAILED',
  'ANON_EVALUATE',
  'SECRETARY_REVIEW',
  'PRINCIPAL_INSTRUCTION',
  'TASKS_ASSIGNED',
  'TASK_SUBMIT',
  'TASK_REVIEW',
  'PRINCIPAL_CONFIRM',
  'PRINCIPAL_REJECT',
  'ARCHIVE',
  'CAPTCHA_RESET',
  'IP_BLACKLISTED',
  'IP_UNBLACKLISTED',
  'USER_CREATED',
  'USER_UPDATED',
  'DEPARTMENT_CREATED',
  'DEPARTMENT_UPDATED',
  'CONFIG_UPDATED',
]

export const AUDIT_ACTION_TEXT: Record<string, string> = {
  LOGIN_SUCCESS: '登录成功',
  LOGIN_FAILED: '登录失败',
  PASSWORD_CHANGED: '修改密码',
  OAUTH_LOGIN: '统一认证登录',
  ANON_SUBMIT: '匿名提交留言',
  ANON_QUERY: '匿名查询留言',
  ANON_QUERY_FAILED: '匿名查询失败',
  ANON_EVALUATE: '匿名评价',
  SECRETARY_REVIEW: '秘书审核留言',
  PRINCIPAL_INSTRUCTION: '院长批示',
  TASKS_ASSIGNED: '分派部门任务',
  TASK_SUBMIT: '部门提交处理',
  TASK_REVIEW: '秘书审核任务',
  PRINCIPAL_CONFIRM: '院长最终确认',
  PRINCIPAL_REJECT: '院长驳回确认',
  ARCHIVE: '归档留言',
  CAPTCHA_RESET: '重置验证码锁定',
  IP_BLACKLISTED: 'IP 自动拉黑',
  IP_UNBLACKLISTED: 'IP 解除拉黑',
  USER_CREATED: '新建用户',
  USER_UPDATED: '更新用户',
  DEPARTMENT_CREATED: '新建部门',
  DEPARTMENT_UPDATED: '更新部门',
  CONFIG_UPDATED: '更新系统配置',
}

export function actionText(action?: string | null): string {
  return (action && AUDIT_ACTION_TEXT[action]) || action || '—'
}

/** 留言状态可选项（用于筛选下拉） */
export const MESSAGE_STATUS_OPTIONS: { value: string; label: string }[] = Object.entries(
  MESSAGE_STATUS_TEXT,
).map(([value, label]) => ({ value, label }))

export const TASK_STATUS_OPTIONS: { value: string; label: string }[] = Object.entries(
  TASK_STATUS_TEXT,
).map(([value, label]) => ({ value, label }))
