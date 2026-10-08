<template>
  <div v-loading="loading">
    <el-breadcrumb separator="/" class="crumb">
      <el-breadcrumb-item :to="{ name: 'principal-messages' }">留言列表</el-breadcrumb-item>
      <el-breadcrumb-item v-if="task" :to="{ name: 'principal-message-detail', params: { id: task.message_id } }">
        留言 #{{ task.message_id }}
      </el-breadcrumb-item>
      <el-breadcrumb-item>任务 #{{ taskId }}</el-breadcrumb-item>
    </el-breadcrumb>

    <template v-if="task">
      <div class="app-card">
        <div class="app-card-title">任务信息</div>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务编号">{{ task.id }}</el-descriptions-item>
          <el-descriptions-item label="所属留言">#{{ task.message_id }} {{ task.message_title }}</el-descriptions-item>
          <el-descriptions-item label="任务标题">{{ task.title }}</el-descriptions-item>
          <el-descriptions-item label="负责部门">{{ task.department_name }}</el-descriptions-item>
          <el-descriptions-item label="分派时间">{{ formatDateTime(task.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="任务状态">
            <el-tag :type="taskStatusType(task.status)">{{ taskStatusText(task.status) }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <el-divider content-position="left">任务内容</el-divider>
        <div class="content-box">{{ task.content || '（无任务内容说明）' }}</div>
      </div>

      <div class="app-card">
        <div class="app-card-title">部门处理结果</div>
        <template v-if="task.processing_content">
          <div class="content-box">{{ task.processing_content }}</div>
          <div class="muted" style="margin-top: 8px">提交时间：{{ formatDateTime(task.submitted_at) }} · 通过时间：{{ formatDateTime(task.approved_at) }}</div>
        </template>
        <span v-else class="muted">部门尚未提交处理内容</span>
      </div>

      <div class="app-card">
        <div class="app-card-title">任务附件</div>
        <template v-if="task.status === 'APPROVED'">
          <AttachmentList :attachments="task.attachments" />
        </template>
        <span v-else class="muted">任务审核通过后附件可见</span>
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
import { useRoute } from 'vue-router'

import * as principalApi from '@/api/principal'
import AttachmentList from '@/components/AttachmentList.vue'
import type { TaskDetail } from '@/types'
import { formatDateTime } from '@/utils/format'
import { reviewResultText, reviewResultType, roleText, taskStatusText, taskStatusType } from '@/utils/status'

const route = useRoute()
const taskId = Number(route.params.taskId)
const task = ref<TaskDetail | null>(null)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await principalApi.getTask(taskId)
    task.value = data
  } catch {
    /* ignore */
  } finally {
    loading.value = false
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

.review-comment {
  margin-top: 4px;
  color: #5b6b7a;
  font-size: 13px;
  white-space: pre-wrap;
}
</style>
