<template>
  <PublicHeader>
    <div class="login-page">
      <div class="app-card login-card">
        <div class="login-head">
          <div class="login-logo">医</div>
          <h2 class="login-title">员工登录</h2>
          <p class="login-sub">医院匿名留言板系统 · 内部工作台</p>
        </div>

        <el-tabs v-model="tab" stretch>
          <!-- 本地账号密码登录 -->
          <el-tab-pane label="本地账号登录" name="local">
            <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
              <el-form-item label="账号" prop="username">
                <el-input v-model="form.username" placeholder="请输入账号" autocomplete="username" @keyup.enter="submit" />
              </el-form-item>
              <el-form-item label="密码" prop="password">
                <el-input
                  v-model="form.password"
                  type="password"
                  show-password
                  placeholder="请输入密码"
                  autocomplete="current-password"
                  @keyup.enter="submit"
                />
              </el-form-item>
              <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon :closable="false" class="login-error" />
              <el-button type="primary" size="large" class="login-btn" :loading="submitting" :disabled="submitting" @click="submit">
                登 录
              </el-button>
            </el-form>
          </el-tab-pane>

          <!-- 统一认证登录 -->
          <el-tab-pane label="统一认证登录" name="oauth">
            <div class="oauth-box">
              <p class="muted">
                使用医院统一认证中心账号登录。首次登录将自动创建本地账号，需管理员分配角色后即可使用。
              </p>
              <el-button type="primary" size="large" class="login-btn" @click="goOAuth">
                前往统一认证中心
              </el-button>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </PublicHeader>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

import { OAUTH_LOGIN_URL } from '@/api/auth'
import { extractApiError } from '@/api/http'
import PublicHeader from '@/components/PublicHeader.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const tab = ref('local')
const formRef = ref<FormInstance>()
const submitting = ref(false)
const errorMsg = ref('')

const form = reactive({ username: '', password: '' })

const rules: FormRules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

function redirectTarget(): string {
  const r = route.query.redirect
  return typeof r === 'string' && r.startsWith('/') ? r : auth.homePath
}

async function submit() {
  if (submitting.value) return
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  submitting.value = true
  errorMsg.value = ''
  try {
    const data = await auth.login(form.username.trim(), form.password)
    if (data.user.must_change_password) {
      ElMessage.warning('首次登录或密码已重置，请先修改密码')
      router.push({ name: 'change-password' })
    } else {
      ElMessage.success(`欢迎，${data.user.display_name || data.user.username}`)
      router.push(redirectTarget())
    }
  } catch (e) {
    const info = extractApiError(e)
    // 423 锁定：展示解锁时间；其余展示错误信息
    errorMsg.value = info.message
  } finally {
    submitting.value = false
  }
}

function goOAuth() {
  window.location.href = OAUTH_LOGIN_URL
}
</script>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  padding-top: 24px;
}

.login-card {
  width: 100%;
  max-width: 420px;
}

.login-head {
  text-align: center;
  margin-bottom: 12px;
}

.login-logo {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: #0e7a78;
  color: #fff;
  font-size: 28px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 10px;
}

.login-title {
  margin: 0 0 4px;
  color: #0b615f;
}

.login-sub {
  margin: 0;
  color: #9aa7b3;
  font-size: 13px;
}

.login-error {
  margin-bottom: 12px;
}

.login-btn {
  width: 100%;
}

.oauth-box {
  padding: 10px 0;
}
</style>
