/** Pinia 认证 store：token 持久化 localStorage、当前用户、登录/登出/拉取用户信息 */
import { defineStore } from 'pinia'

import * as authApi from '@/api/auth'
import { TOKEN_KEY, USER_KEY } from '@/api/http'
import type { User } from '@/types'

function readStoredUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as User) : null
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: readStoredUser(),
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
    role: (state) => state.user?.role ?? '',
    displayName: (state) => state.user?.display_name || state.user?.username || '',
    /** 按角色返回登录后的首页地址 */
    homePath(state): string {
      switch (state.user?.role) {
        case 'principal':
          return '/principal'
        case 'secretary':
          return '/secretary'
        case 'department':
          return '/department'
        case 'admin':
          return '/admin/users'
        default:
          return '/login'
      }
    },
  },

  actions: {
    setAuth(token: string, user: User | null) {
      this.token = token
      this.user = user
      localStorage.setItem(TOKEN_KEY, token)
      if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
    },

    setUser(user: User) {
      this.user = user
      localStorage.setItem(USER_KEY, JSON.stringify(user))
    },

    /** 本地账号密码登录 */
    async login(username: string, password: string) {
      const { data } = await authApi.login(username, password)
      this.setAuth(data.token, data.user)
      return data
    },

    /** 拉取当前用户（启动/守卫时校验 token 有效性） */
    async fetchMe() {
      const { data } = await authApi.me()
      this.setUser(data)
      return data
    },

    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    },
  },
})
