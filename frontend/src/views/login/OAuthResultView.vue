<template>
  <PublicHeader>
    <div class="oauth-page">
      <el-result v-if="state === 'error'" icon="error" title="统一认证登录失败" :sub-title="message">
        <template #extra>
          <el-button type="primary" @click="$router.push({ name: 'login' })">返回登录</el-button>
        </template>
      </el-result>

      <el-result v-else-if="state === 'pending'" icon="info" :title="`账号已创建，等待管理员授权`" :sub-title="pendingText">
        <template #extra>
          <el-button type="primary" @click="$router.push({ name: 'login' })">返回登录</el-button>
        </template>
      </el-result>

      <el-result v-else-if="state === 'done'" icon="success" title="登录成功" sub-title="正在进入工作台…" />

      <el-result v-else icon="warning" title="无效的回调" sub-title="缺少必要的回调参数，请重新发起统一认证登录。">
        <template #extra>
          <el-button type="primary" @click="$router.push({ name: 'login' })">返回登录</el-button>
        </template>
      </el-result>
    </div>
  </PublicHeader>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import PublicHeader from '@/components/PublicHeader.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

type State = 'loading' | 'error' | 'pending' | 'done' | 'invalid'
const state = ref<State>('loading')
const message = ref('')
const pendingText = ref('')

/** 后端以 urlencode({"u": name}) / urlencode({"e": err}) 传递文本参数 */
function parseWrapped(v: unknown): string {
  const raw = typeof v === 'string' ? v : ''
  try {
    const obj = JSON.parse(raw) as Record<string, unknown>
    const keys = Object.keys(obj)
    if (keys.length > 0 && typeof obj[keys[0]] === 'string') return obj[keys[0]] as string
  } catch {
    /* ignore */
  }
  return raw
}

const hasPending = computed(() => String(route.query.pending ?? '') === '1')

onMounted(async () => {
  const token = route.query.token
  const username = parseWrapped(route.query.username)
  const error = parseWrapped(route.query.error)

  if (typeof token === 'string' && token) {
    try {
      auth.setAuth(token, null)
      await auth.fetchMe()
      if (auth.user?.must_change_password) {
        router.replace({ name: 'change-password' })
      } else {
        router.replace(auth.homePath)
      }
      state.value = 'done'
    } catch {
      auth.logout()
      message.value = '登录信息校验失败，请重新登录'
      state.value = 'error'
    }
    return
  }

  if (hasPending.value) {
    state.value = 'pending'
    pendingText.value = username ? `账号「${username}」已创建，请联系管理员分配角色与部门并启用账号。` : '请联系管理员分配角色与部门并启用账号。'
    return
  }

  if (error) {
    state.value = 'error'
    message.value = error
    return
  }

  state.value = 'invalid'
})
</script>

<style scoped>
.oauth-page {
  max-width: 640px;
  margin: 0 auto;
  padding-top: 24px;
}
</style>
