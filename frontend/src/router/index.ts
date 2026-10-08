/**
 * 路由与守卫：
 * - 匿名端（/ /submit/success /query /evaluate/:id /oauth2/result /login）无需登录
 * - 登录后按角色跳转对应工作台首页
 * - must_change_password=true 时强制跳转修改密码页
 * - 角色不匹配时跳回本角色首页
 */
import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import MainLayout from '@/layouts/MainLayout.vue'

import SubmitView from '@/views/anonymous/SubmitView.vue'
import SubmitSuccessView from '@/views/anonymous/SubmitSuccessView.vue'
import QueryView from '@/views/anonymous/QueryView.vue'
import EvaluateView from '@/views/anonymous/EvaluateView.vue'
import OAuthResultView from '@/views/login/OAuthResultView.vue'
import LoginView from '@/views/login/LoginView.vue'
import ChangePasswordView from '@/views/login/ChangePasswordView.vue'

import PrincipalMessageListView from '@/views/principal/MessageListView.vue'
import PrincipalMessageDetailView from '@/views/principal/MessageDetailView.vue'
import PrincipalTaskDetailView from '@/views/principal/TaskDetailView.vue'

import SecretaryMessageListView from '@/views/secretary/MessageListView.vue'
import SecretaryMessageDetailView from '@/views/secretary/MessageDetailView.vue'
import SecretaryTaskListView from '@/views/secretary/TaskListView.vue'
import SecretaryTaskDetailView from '@/views/secretary/TaskDetailView.vue'

import DepartmentTaskListView from '@/views/department/TaskListView.vue'
import DepartmentTaskDetailView from '@/views/department/TaskDetailView.vue'

import AdminUsersView from '@/views/admin/UsersView.vue'
import AdminDepartmentsView from '@/views/admin/DepartmentsView.vue'
import AdminConfigsView from '@/views/admin/ConfigsView.vue'
import AdminLogsView from '@/views/admin/LogsView.vue'
import AdminCaptchaResetView from '@/views/admin/CaptchaResetView.vue'
import AdminBlacklistView from '@/views/admin/BlacklistView.vue'

import NotFoundView from '@/views/NotFoundView.vue'

declare module 'vue-router' {
  interface RouteMeta {
    /** 匿名可访问 */
    public?: boolean
    /** 允许的角色列表；缺省表示仅需登录 */
    roles?: string[]
    /** 页面标题 */
    title?: string
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // ---------------- 匿名端（无需登录） ----------------
    { path: '/', name: 'submit', component: SubmitView, meta: { public: true, title: '我要留言' } },
    { path: '/submit/success', name: 'submit-success', component: SubmitSuccessView, meta: { public: true, title: '提交成功' } },
    { path: '/query', name: 'query', component: QueryView, meta: { public: true, title: '进度查询' } },
    { path: '/evaluate/:id', name: 'evaluate', component: EvaluateView, meta: { public: true, title: '匿名评价' } },
    { path: '/oauth2/result', name: 'oauth-result', component: OAuthResultView, meta: { public: true, title: '统一认证结果' } },
    { path: '/login', name: 'login', component: LoginView, meta: { public: true, title: '员工登录' } },

    // ---------------- 修改密码（登录后强制/自愿） ----------------
    { path: '/change-password', name: 'change-password', component: ChangePasswordView, meta: { title: '修改密码' } },

    // ---------------- 院长工作台 ----------------
    {
      path: '/principal',
      component: MainLayout,
      meta: { roles: ['principal'] },
      children: [
        { path: '', name: 'principal-messages', component: PrincipalMessageListView, meta: { title: '留言列表' } },
        { path: 'messages/:id', name: 'principal-message-detail', component: PrincipalMessageDetailView, meta: { title: '留言详情' } },
        { path: 'tasks/:taskId', name: 'principal-task-detail', component: PrincipalTaskDetailView, meta: { title: '任务详情' } },
      ],
    },

    // ---------------- 秘书工作台 ----------------
    {
      path: '/secretary',
      component: MainLayout,
      meta: { roles: ['secretary'] },
      children: [
        { path: '', name: 'secretary-messages', component: SecretaryMessageListView, meta: { title: '留言列表' } },
        { path: 'messages/:id', name: 'secretary-message-detail', component: SecretaryMessageDetailView, meta: { title: '留言详情' } },
        { path: 'tasks', name: 'secretary-tasks', component: SecretaryTaskListView, meta: { title: '任务列表' } },
        { path: 'tasks/:taskId', name: 'secretary-task-detail', component: SecretaryTaskDetailView, meta: { title: '任务详情' } },
      ],
    },

    // ---------------- 部门工作台 ----------------
    {
      path: '/department',
      component: MainLayout,
      meta: { roles: ['department'] },
      children: [
        { path: '', name: 'department-tasks', component: DepartmentTaskListView, meta: { title: '任务列表' } },
        { path: 'tasks/:taskId', name: 'department-task-detail', component: DepartmentTaskDetailView, meta: { title: '任务详情' } },
      ],
    },

    // ---------------- 管理员工作台 ----------------
    {
      path: '/admin',
      component: MainLayout,
      meta: { roles: ['admin'] },
      children: [
        { path: '', redirect: { name: 'admin-users' } },
        { path: 'users', name: 'admin-users', component: AdminUsersView, meta: { title: '用户管理' } },
        { path: 'departments', name: 'admin-departments', component: AdminDepartmentsView, meta: { title: '部门管理' } },
        { path: 'configs', name: 'admin-configs', component: AdminConfigsView, meta: { title: '系统配置' } },
        { path: 'logs', name: 'admin-logs', component: AdminLogsView, meta: { title: '日志查询' } },
        { path: 'captcha-reset', name: 'admin-captcha-reset', component: AdminCaptchaResetView, meta: { title: '验证码重置' } },
        { path: 'blacklist', name: 'admin-blacklist', component: AdminBlacklistView, meta: { title: 'IP 黑名单' } },
      ],
    },

    // ---------------- 404 ----------------
    { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundView, meta: { public: true, title: '页面不存在' } },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  document.title = to.meta.title ? `${to.meta.title} · 医院匿名留言板系统` : '医院匿名留言板系统'

  // 匿名可访问页面
  if (to.meta.public) {
    // 已登录用户访问登录页 → 跳回角色首页
    if (to.name === 'login' && auth.isAuthenticated) {
      if (!auth.user) {
        try {
          await auth.fetchMe()
        } catch {
          auth.logout()
          return true
        }
      }
      return auth.homePath
    }
    return true
  }

  // 需要登录
  if (!auth.token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // 有 token 但内存中没有用户 → 拉取 /me 校验
  if (!auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      auth.logout()
      return { name: 'login', query: { redirect: to.fullPath } }
    }
  }

  const user = auth.user
  if (!user) {
    auth.logout()
    return { name: 'login' }
  }

  // 未授权（统一认证新用户 role 为空）→ 登出并提示
  if (!user.role) {
    auth.logout()
    return { name: 'login' }
  }

  // 强制修改密码
  if (user.must_change_password && to.path !== '/change-password') {
    return { path: '/change-password' }
  }

  // 角色守卫
  const roles = to.meta.roles
  if (roles && roles.length > 0 && !roles.includes(user.role)) {
    return auth.homePath
  }

  return true
})

export default router
