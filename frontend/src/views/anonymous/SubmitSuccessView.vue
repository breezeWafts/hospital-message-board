<template>
  <PublicHeader>
    <div class="success-page">
      <el-result icon="success" title="留言提交成功" sub-title="我们已收到您的留言，工作人员将尽快处理。">
        <template #extra>
          <div class="credential-card">
            <div class="credential-warn">
              <el-icon><WarningFilled /></el-icon>
              <span>请立即截图保存以下信息，用于后续查询进度与结果！</span>
            </div>
            <div class="credential-item">
              <div class="credential-label">留言编号</div>
              <div class="credential-value">{{ result.id }}</div>
              <el-button size="small" text type="primary" @click="copy(String(result.id))">复制</el-button>
            </div>
            <div class="credential-item">
              <div class="credential-label">查询验证码</div>
              <div class="credential-value captcha">{{ result.captcha }}</div>
              <el-button size="small" text type="primary" @click="copy(result.captcha)">复制</el-button>
            </div>
          </div>
          <div class="success-actions">
            <el-button type="primary" size="large" @click="goQuery">去查询进度</el-button>
            <el-button size="large" @click="$router.push({ name: 'submit' })">再写一条</el-button>
          </div>
        </template>
      </el-result>

      <el-alert
        v-if="!hasResult"
        type="warning"
        :closable="false"
        show-icon
        title="未找到本次提交结果（可能是直接访问本页）。请前往“我要留言”重新提交。"
        style="margin-top: 16px"
      />
    </div>
  </PublicHeader>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import PublicHeader from '@/components/PublicHeader.vue'
import type { AnonymousSubmitResult } from '@/types'

const router = useRouter()

/** history.state 优先，sessionStorage 兜底（刷新后仍可展示） */
const result = computed<AnonymousSubmitResult>(() => {
  const state = history.state as AnonymousSubmitResult | null
  if (state && typeof state.id === 'number' && typeof state.captcha === 'string') {
    return state
  }
  try {
    const raw = sessionStorage.getItem('hmb_submit_result')
    if (raw) {
      const parsed = JSON.parse(raw) as AnonymousSubmitResult
      if (typeof parsed.id === 'number' && typeof parsed.captcha === 'string') return parsed
    }
  } catch {
    /* ignore */
  }
  return { id: 0, captcha: '', message: '' }
})

const hasResult = computed(() => result.value.id > 0 && !!result.value.captcha)

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.warning('复制失败，请手动记录')
  }
}

function goQuery() {
  if (!hasResult.value) return
  sessionStorage.setItem('hmb_query_id', String(result.value.id))
  sessionStorage.setItem('hmb_query_captcha', result.value.captcha)
  router.push({ name: 'query' })
}
</script>

<style scoped>
.success-page {
  max-width: 680px;
  margin: 0 auto;
}

.credential-card {
  background: #fff;
  border: 1px solid #e6ecec;
  border-radius: 12px;
  padding: 18px 20px;
  margin-bottom: 20px;
}

.credential-warn {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #e6a23c;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 14px;
}

.credential-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px dashed #eef2f2;
}

.credential-item:last-child {
  border-bottom: none;
}

.credential-label {
  width: 90px;
  color: #7a8a99;
  font-size: 14px;
  flex-shrink: 0;
}

.credential-value {
  flex: 1;
  font-size: 22px;
  font-weight: 700;
  color: #0b615f;
  letter-spacing: 1px;
}

.credential-value.captcha {
  font-family: 'Courier New', Consolas, monospace;
  color: #e6a23c;
  letter-spacing: 3px;
}

.success-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
