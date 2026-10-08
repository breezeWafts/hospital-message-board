<template>
  <div class="pwd-page">
    <div class="app-card pwd-card">
      <div class="pwd-head">
        <div class="pwd-logo">医</div>
        <h2 class="pwd-title">修改密码</h2>
        <p v-if="forced" class="pwd-sub">首次登录或密码已被重置，请先设置新密码（至少 8 位，须同时包含字母和数字）</p>
        <p v-else class="pwd-sub">为保障账号安全，请定期修改密码</p>
      </div>
      <ChangePasswordForm @success="onSuccess" />
      <el-button v-if="!forced" text @click="router.push(auth.homePath)">返回工作台</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import ChangePasswordForm from '@/components/ChangePasswordForm.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const forced = computed(() => !!auth.user?.must_change_password)

function onSuccess() {
  ElMessage.success('密码已更新，进入工作台')
  router.push(auth.homePath)
}
</script>

<style scoped>
.pwd-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f7f7;
  padding: 16px;
}

.pwd-card {
  width: 100%;
  max-width: 460px;
  margin: 0;
}

.pwd-head {
  text-align: center;
  margin-bottom: 16px;
}

.pwd-logo {
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

.pwd-title {
  margin: 0 0 4px;
  color: #0b615f;
}

.pwd-sub {
  margin: 0;
  color: #9aa7b3;
  font-size: 13px;
}
</style>
