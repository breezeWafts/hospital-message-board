<template>
  <div v-loading="loading">
    <el-breadcrumb separator="/" class="crumb">
      <el-breadcrumb-item :to="{ name: 'secretary-tasks' }">任务列表</el-breadcrumb-item>
      <el-breadcrumb-item>任务 #{{ taskId }}</el-breadcrumb-item>
    </el-breadcrumb>

    <template v-if="task">
      <div class="app-card">
        <div class="app-card-title">任务信息</div>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务编号">{{ task.id }}</el-descriptions-item>
          <el-descriptions-item label="所属留言">
            <el-link type="primary" :underline="false" @click="goMessage">{{ `#${task.message_id} ${task.message_title}` }}</el-link>
          </el-descriptions-item>
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

      <!-- 审核操作 -->
      <div v-if="task.status === 'REVIEWING'" class="app-card review-card">
        <div class="app-card-title">任务审核</div>
        <el-input v-model="comment" type="textarea" :rows="3" maxlength="2000" show-word-limit placeholder="审核意见（驳回时必填批注）" />
        <div class="actions">
          <el-button type="success" :loading="reviewing" :disabled="reviewing" @click="doReview('APPROVED')">通过</el-button>
          <el-button type="danger" plain :loading="reviewing" :disabled="reviewing" @click="doReview('REJECTED')">驳回</el-button>
        </div>
      </div>

      <div class="app-card">
        <div class="app-card-title">部门处理内容</div>
        <div v-if="task.processing_content" class="content-box">{{ task.processing_content }}</div>
        <span v-else class="muted">部门尚未提交处理内容</span>
      </div>

      <div class="app-card">
        <div class="app-card-title">任务附件</div>
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
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import * as secretaryApi from '@/api/secretary'
import AttachmentList from '@/components/AttachmentList.vue'
import type { TaskDetail } from '@/types'
import { formatDateTime } from '@/utils/format'
import { reviewResultText, reviewResultType, roleText, taskStatusText, taskStatusType } from '@/utils/status'

const route = useRoute()
const router = useRouter()

const taskId = Number(route.params.taskId)
const task = ref<TaskDetail | null>(null)
const loading = ref(false)
const comment = ref('')
const reviewing = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await secretaryApi.getTask(taskId)
    task.value = data
  } catch {
    /* ignore */
  } finally {
    loading.value = false
  }
}

async function doReview(result: 'APPROVED' | 'REJECTED') {
  if (result === 'REJECTED' && !comment.value.trim()) {
    ElMessage.warning('驳回必须填写批注')
    return
  }
  if (result === 'REJECTED') {
    try {
      await ElMessageBox.confirm('确定驳回该任务？任务将退回部门重新处理。', '确认驳回', {
        confirmButtonText: '驳回',
        cancelButtonText: '取消',
        type: 'warning',
      })
    } catch {
      return
    }
  }
  reviewing.value = true
  try {
    await secretaryApi.reviewTask(taskId, result, comment.value.trim() || undefined)
    ElMessage.success('审核完成')
    comment.value = ''
    await load()
  } catch {
    /* ignore */
  } finally {
    reviewing.value = false
  }
}

function goMessage() {
  if (task.value) {
    router.push({ name: 'secretary-message-detail', params: { id: task.value.message_id } })
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

.actions {
  display: flex;
  gap: 12px;
  margin-top: 12px;
}

.review-card {
  border-left: 4px solid #e6a23c;
}

.review-comment {
  margin-top: 4px;
  color: #5b6b7a;
  font-size: 13px;
  white-space: pre-wrap;
}
</style>
