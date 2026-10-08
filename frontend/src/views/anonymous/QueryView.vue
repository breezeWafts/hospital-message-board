<template>
  <PublicHeader>
    <div class="query-page">
      <div class="page-hero">
        <h1 class="hero-title">留言进度查询</h1>
        <p class="hero-sub">输入提交时获得的<strong>留言编号</strong>与<strong>查询验证码</strong>，即可查询处理进度与结果。</p>
      </div>

      <!-- 查询表单 -->
      <div class="app-card">
        <el-form :inline="true" class="query-form" @submit.prevent="submit">
          <el-form-item label="留言编号">
            <el-input-number v-model="form.id" :min="1" :controls="false" placeholder="编号" class="id-input" />
          </el-form-item>
          <el-form-item label="查询验证码">
            <el-input v-model="form.captcha" placeholder="6 位验证码" maxlength="16" class="captcha-input" @keyup.enter="submit" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" :disabled="loading" @click="submit">查询</el-button>
          </el-form-item>
        </el-form>

        <el-alert
          v-if="errorMsg"
          :title="errorMsg"
          type="error"
          show-icon
          :closable="false"
          class="query-error"
        />
      </div>

      <!-- 未完成：仅基础状态 -->
      <div v-if="basic" class="app-card">
        <div class="app-card-title">查询结果</div>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="留言编号">{{ basic.id }}</el-descriptions-item>
          <el-descriptions-item label="标题">{{ basic.title }}</el-descriptions-item>
          <el-descriptions-item label="当前状态">
            <el-tag :type="messageStatusType(basic.status)">{{ messageStatusText(basic.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="提交时间">{{ formatDateTime(basic.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="最近更新">{{ formatDateTime(basic.updated_at) }}</el-descriptions-item>
          <el-descriptions-item label="验证码有效期至">{{ formatDateTime(basic.captcha_expires_at) }}</el-descriptions-item>
        </el-descriptions>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="您的留言正在处理中"
          description="留言处理完成后，可再次查询查看完整的处理历史与结果，并进行满意度评价。"
          style="margin-top: 14px"
        />
      </div>

      <!-- 已完成/已归档：完整详情 -->
      <div v-if="detail">
        <div class="app-card">
          <div class="app-card-title">留言详情</div>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="留言编号">{{ detail.id }}</el-descriptions-item>
            <el-descriptions-item label="当前状态">
              <el-tag :type="messageStatusType(detail.status)">{{ messageStatusText(detail.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="标题">{{ detail.title }}</el-descriptions-item>
            <el-descriptions-item label="提交时间">{{ formatDateTime(detail.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="完成时间">{{ formatDateTime(detail.completed_at) }}</el-descriptions-item>
            <el-descriptions-item label="归档时间">{{ formatDateTime(detail.archived_at) }}</el-descriptions-item>
          </el-descriptions>
          <el-divider content-position="left">留言内容</el-divider>
          <div class="content-box">{{ detail.content }}</div>
        </div>

        <!-- 工作流 -->
        <div class="app-card">
          <div class="app-card-title">处理流程</div>
          <WorkflowGraph :workflow="detail.workflow" />
        </div>

        <!-- 秘书审核 / 院长批示 -->
        <div class="app-card">
          <div class="app-card-title">审核与批示</div>
          <el-timeline>
            <el-timeline-item
              v-for="(r, i) in detail.reviews"
              :key="i"
              :timestamp="formatDateTime(r.created_at)"
              :type="r.result === 'APPROVED' ? 'success' : 'danger'"
            >
              <div>
                <el-tag :type="reviewResultType(r.result)" size="small">{{ reviewResultText(r.result) }}</el-tag>
                <span class="muted">（{{ r.reviewer_name }} · {{ roleText(r.role) }}）</span>
                <div v-if="r.comment" class="review-comment">{{ r.comment }}</div>
              </div>
            </el-timeline-item>
          </el-timeline>
          <div v-if="detail.principal_instruction" class="instruction-box">
            <div class="instruction-title">院长批示</div>
            <div>{{ detail.principal_instruction }}</div>
          </div>
        </div>

        <!-- 留言附件 -->
        <div class="app-card">
          <div class="app-card-title">留言附件</div>
          <AttachmentList :attachments="detail.attachments || []" />
        </div>

        <!-- 部门任务与处理内容 -->
        <div class="app-card">
          <div class="app-card-title">部门处理记录</div>
          <div v-if="detail.tasks.length === 0" class="muted">暂无部门处理记录</div>
          <div v-for="t in detail.tasks" :key="t.id" class="task-block">
            <div class="task-head">
              <span class="task-title">{{ t.title }}</span>
              <el-tag size="small" :type="taskStatusType(t.status)">{{ taskStatusText(t.status) }}</el-tag>
              <span class="muted">{{ t.department_name }} · 处理完成于 {{ formatDateTime(t.approved_at || t.submitted_at) }}</span>
            </div>
            <div v-if="t.processing_content" class="processing-box">{{ t.processing_content }}</div>
            <div v-if="t.attachments.length > 0" class="task-attachments">
              <AttachmentList :attachments="t.attachments" />
            </div>
            <div v-if="t.reviews.length > 0" class="task-reviews">
              <div v-for="(r, i) in t.reviews" :key="i" class="task-review-line">
                <el-tag :type="reviewResultType(r.result)" size="small">{{ reviewResultText(r.result) }}</el-tag>
                <span class="muted">{{ r.reviewer_name }}（{{ roleText(r.role) }}）· {{ formatDateTime(r.created_at) }}</span>
                <div v-if="r.comment" class="review-comment">{{ r.comment }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 评价 -->
        <div class="app-card">
          <div class="app-card-title">满意度评价</div>
          <template v-if="detail.evaluation_satisfied === true">
            <el-alert type="success" :closable="false" show-icon title="您已评价：满意" />
          </template>
          <template v-else-if="detail.evaluation_satisfied === false">
            <el-alert type="warning" :closable="false" show-icon title="您已评价：不满意" />
          </template>
          <template v-else-if="detail.can_evaluate">
            <el-alert
              type="success"
              :closable="false"
              show-icon
              title="处理已完成，欢迎评价"
              description="请对本次处理结果进行评价，您的意见对我们很重要。"
              style="margin-bottom: 14px"
            />
            <el-form label-position="top">
              <el-form-item label="是否满意？">
                <el-radio-group v-model="evalForm.satisfied">
                  <el-radio :value="true">满意</el-radio>
                  <el-radio :value="false">不满意</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="评价内容（可选）">
                <el-input v-model="evalForm.content" type="textarea" :rows="3" maxlength="2000" show-word-limit />
              </el-form-item>
              <el-button type="primary" :loading="evalSubmitting" :disabled="evalSubmitting" @click="submitEvaluate">
                提交评价
              </el-button>
              <el-button text type="primary" @click="goEvaluatePage">前往评价页</el-button>
            </el-form>
          </template>
          <template v-else>
            <span class="muted">当前留言暂不支持评价（可能已归档或未完成）。</span>
          </template>
        </div>
      </div>
    </div>
  </PublicHeader>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import * as anonymousApi from '@/api/anonymous'
import { extractApiError } from '@/api/http'
import AttachmentList from '@/components/AttachmentList.vue'
import PublicHeader from '@/components/PublicHeader.vue'
import WorkflowGraph from '@/components/workflow/WorkflowGraph.vue'
import type { AnonymousBasicResult, MessageDetail } from '@/types'
import { formatDateTime } from '@/utils/format'
import {
  messageStatusText,
  messageStatusType,
  reviewResultText,
  reviewResultType,
  roleText,
  taskStatusText,
  taskStatusType,
} from '@/utils/status'

const router = useRouter()

const form = reactive({ id: 1 as number | null, captcha: '' })
const loading = ref(false)
const errorMsg = ref('')
const basic = ref<AnonymousBasicResult | null>(null)
const detail = ref<MessageDetail | null>(null)

function evalCaptchaKey(id: number) {
  return `hmb_eval_captcha_${id}`
}

onMounted(() => {
  // 从提交成功页带过来的预填
  const pid = sessionStorage.getItem('hmb_query_id')
  const pc = sessionStorage.getItem('hmb_query_captcha')
  if (pid && pc) {
    form.id = Number(pid) || 1
    form.captcha = pc
    sessionStorage.removeItem('hmb_query_id')
    sessionStorage.removeItem('hmb_query_captcha')
    void submit()
  }
})

async function submit() {
  if (loading.value) return
  if (!form.id || !form.captcha.trim()) {
    errorMsg.value = '请输入留言编号与查询验证码'
    return
  }
  loading.value = true
  errorMsg.value = ''
  basic.value = null
  detail.value = null
  try {
    const { data } = await anonymousApi.queryMessage(form.id, form.captcha.trim())
    if ((data as MessageDetail).workflow) {
      detail.value = data as MessageDetail
      if (detail.value.can_evaluate) {
        sessionStorage.setItem(evalCaptchaKey(detail.value.id), form.captcha.trim())
      }
    } else {
      basic.value = data as AnonymousBasicResult
    }
  } catch (e) {
    errorMsg.value = extractApiError(e).message
  } finally {
    loading.value = false
  }
}

// ---------------- 评价 ----------------
const evalSubmitting = ref(false)
const evalForm = reactive({ satisfied: true, content: '' })

function currentCaptcha(): string {
  const id = detail.value?.id
  if (!id) return form.captcha.trim()
  return sessionStorage.getItem(evalCaptchaKey(id)) || form.captcha.trim()
}

async function submitEvaluate() {
  if (!detail.value || evalSubmitting.value) return
  evalSubmitting.value = true
  try {
    const { data } = await anonymousApi.evaluateMessage(
      detail.value.id,
      currentCaptcha(),
      evalForm.satisfied,
      evalForm.content.trim() || undefined,
    )
    ElMessage.success(data.status === 'ARCHIVED' ? '评价成功，留言已归档' : '评价成功')
    await submit() // 刷新详情
  } catch (e) {
    errorMsg.value = extractApiError(e).message
    ElMessage.error(errorMsg.value)
  } finally {
    evalSubmitting.value = false
  }
}

function goEvaluatePage() {
  if (!detail.value) return
  sessionStorage.setItem(evalCaptchaKey(detail.value.id), currentCaptcha())
  router.push({ name: 'evaluate', params: { id: detail.value.id } })
}
</script>

<style scoped>
.page-hero {
  text-align: center;
  padding: 8px 0 20px;
}

.hero-title {
  font-size: 26px;
  color: #0b615f;
  margin: 0 0 8px;
}

.hero-sub {
  color: #7a8a99;
  font-size: 14px;
  margin: 0;
}

.query-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.id-input {
  width: 160px;
}

.captcha-input {
  width: 180px;
}

.query-error {
  margin-top: 8px;
}

.content-box {
  background: #fafcfc;
  border: 1px solid #eef2f2;
  border-radius: 8px;
  padding: 14px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.8;
}

.review-comment {
  margin-top: 4px;
  color: #5b6b7a;
  font-size: 13px;
  white-space: pre-wrap;
}

.instruction-box {
  margin-top: 12px;
  background: #f5faf9;
  border: 1px solid #d8ebe9;
  border-radius: 8px;
  padding: 12px 14px;
  line-height: 1.8;
  white-space: pre-wrap;
}

.instruction-title {
  color: #0b615f;
  font-weight: 600;
  margin-bottom: 4px;
}

.task-block {
  border: 1px solid #e6ecec;
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 12px;
}

.task-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.task-title {
  font-weight: 600;
  color: #2c3e50;
}

.processing-box {
  background: #fafcfc;
  border-radius: 8px;
  padding: 10px 12px;
  white-space: pre-wrap;
  line-height: 1.8;
  margin-bottom: 10px;
}

.task-attachments {
  margin-bottom: 8px;
}

.task-review-line {
  padding: 4px 0;
  font-size: 13px;
}
</style>
