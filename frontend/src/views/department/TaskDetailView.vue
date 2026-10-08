<template>
  <div v-loading="loading">
    <el-breadcrumb separator="/" class="crumb">
      <el-breadcrumb-item :to="{ name: 'department-tasks' }">任务列表</el-breadcrumb-item>
      <el-breadcrumb-item>任务 #{{ taskId }}</el-breadcrumb-item>
    </el-breadcrumb>

    <template v-if="task">
      <!-- 驳回批注 -->
      <el-alert
        v-if="task.last_review_result === 'REJECTED' && task.last_review_comment"
        type="error"
        show-icon
        :closable="false"
        title="该任务曾被驳回，请按批注重新处理"
        :description="task.last_review_comment"
        style="margin-bottom: 14px"
      />

      <div class="app-card">
        <div class="app-card-title">任务信息</div>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务编号">{{ task.id }}</el-descriptions-item>
          <el-descriptions-item label="所属留言">#{{ task.message_id }} {{ task.message_title }}</el-descriptions-item>
          <el-descriptions-item label="任务标题">{{ task.title }}</el-descriptions-item>
          <el-descriptions-item label="负责部门">{{ task.department_name }}</el-descriptions-item>
          <el-descriptions-item label="分派人">{{ task.assigner_name }}</el-descriptions-item>
          <el-descriptions-item label="分派时间">{{ formatDateTime(task.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="任务状态">
            <el-tag :type="taskStatusType(task.status)">{{ taskStatusText(task.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="提交时间">{{ formatDateTime(task.submitted_at) }}</el-descriptions-item>
        </el-descriptions>
        <el-divider content-position="left">任务内容</el-divider>
        <div class="content-box">{{ task.content || '（无任务内容说明）' }}</div>
      </div>

      <!-- 提交处理（PENDING：首次处理或被驳回后重新提交） -->
      <div v-if="task.status === 'PENDING'" class="app-card process-card">
        <div class="app-card-title">{{ task.processing_content ? '重新提交处理' : '提交处理' }}</div>
        <el-form label-position="top">
          <el-form-item label="处理内容（必填）">
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="6"
              maxlength="20000"
              show-word-limit
              placeholder="请填写本部门处理情况、结果或答复"
            />
          </el-form-item>
          <el-form-item label="处理附件（可选，可多个）">
            <AttachmentUploader v-model:files="form.files" />
          </el-form-item>
          <el-button type="primary" :loading="submitting" :disabled="submitting" @click="submit">
            提交处理
          </el-button>
        </el-form>
      </div>

      <!-- 已提交/已审核：展示处理结果 -->
      <div v-else class="app-card">
        <div class="app-card-title">已提交的处理内容</div>
        <div class="content-box">{{ task.processing_content || '—' }}</div>
        <div class="muted" style="margin-top: 8px">提交时间：{{ formatDateTime(task.submitted_at) }} · 审核通过时间：{{ formatDateTime(task.approved_at) }}</div>
      </div>

      <div class="app-card">
        <div class="app-card-title">处理附件</div>
        <AttachmentList :attachments="task.attachments" />
      </div>

      <div class="app-card">
        <div class="app-card-title">审核历史</div>
        <el-timeline v-if="task.reviews.length > 0">
          <el-timeline-item
            v-for="(r, i) in task.reviews"
            :key="i"
            :timestamp="formatDateTime(r.created_at)"
            :type="r.result === 'APPROVED' ? 'success' : 'danger'"
          >
            <el-tag :type="reviewResultType(r.result)" size="small">{{ reviewResultText(r.result) }}</el-tag>
            <span class="muted"> {{ r.reviewer_name }}（{{ roleText(r.role) }}）</span>
            <div v-if="r.comment" class="review-comment">{{ r.comment }}</div>
          </el-timeline-item>
        </el-timeline>
        <span v-else class="muted">暂无审核记录</span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import * as departmentApi from '@/api/department'
import { extractApiError } from '@/api/http'
import AttachmentList from '@/components/AttachmentList.vue'
import AttachmentUploader from '@/components/AttachmentUploader.vue'
import type { TaskDetail } from '@/types'
import { formatDateTime } from '@/utils/format'
import { reviewResultText, reviewResultType, roleText, taskStatusText, taskStatusType } from '@/utils/status'

const route = useRoute()
const taskId = Number(route.params.taskId)

const task = ref<TaskDetail | null>(null)
const loading = ref(false)
const form = reactive({ content: '', files: [] as File[] })
const submitting = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await departmentApi.getTask(taskId)
    task.value = data
    if (data.processing_content) form.content = data.processing_content
  } catch {
    /* ignore */
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (submitting.value) return
  if (!form.content.trim()) {
    ElMessage.warning('请填写处理内容')
    return
  }
  submitting.value = true
  const fd = new FormData()
  fd.append('content', form.content.trim())
  form.files.forEach((f) => fd.append('attachments', f))
  try {
    await departmentApi.submitTask(taskId, fd)
    ElMessage.success('已提交，等待秘书审核')
    form.files = []
    await load()
  } catch (e) {
    ElMessage.error(extractApiError(e).message)
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.crumb {
  margin-bottom: 14px;
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

.process-card {
  border-left: 4px solid #0e7a78;
}

.review-comment {
  margin-top: 4px;
  color: #5b6b7a;
  font-size: 13px;
  white-space: pre-wrap;
}
</style>
