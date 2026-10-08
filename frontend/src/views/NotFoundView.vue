<template>
  <div class="nf-page">
    <el-result icon="warning" title="404" sub-title="您访问的页面不存在或已被移除">
      <template #extra>
        <el-button type="primary" @click="goHome">返回首页</el-button>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

function goHome() {
  router.push(auth.isAuthenticated ? auth.homePath : { name: 'submit' })
}
</script>

<style scoped>
.nf-page {
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
