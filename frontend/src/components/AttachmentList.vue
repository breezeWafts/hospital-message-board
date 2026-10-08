<template>
  <div v-if="attachments.length > 0" class="attachment-list">
    <div v-for="att in attachments" :key="att.id" class="attachment-item">
      <div class="attachment-main">
        <el-icon class="file-icon" :class="iconClass(att)"><component :is="iconName(att)" /></el-icon>
        <div class="attachment-info">
          <div class="attachment-name" :title="att.original_name">{{ att.original_name }}</div>
          <div class="attachment-meta">{{ formatBytes(att.size_bytes) }} · {{ formatDateTime(att.created_at) }}</div>
        </div>
      </div>
      <el-button
        size="small"
        type="primary"
        plain
        :loading="downloading === att.id"
        :icon="Download"
        @click="onDownload(att)"
      >
        下载
      </el-button>
    </div>
  </div>
  <div v-else class="attachment-empty">
    <el-empty :image-size="48" description="暂无附件" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Download } from '@element-plus/icons-vue'

import { downloadAttachment } from '@/api/http'
import type { Attachment } from '@/types'
import { formatBytes, formatDateTime } from '@/utils/format'

defineProps<{ attachments: Attachment[] }>()

const downloading = ref<number | null>(null)

function iconName(att: Attachment): string {
  const mime = att.mime_type || ''
  const name = att.original_name.toLowerCase()
  if (mime.startsWith('image/')) return 'Picture'
  if (mime.includes('pdf') || name.endsWith('.pdf')) return 'Document'
  if (name.endsWith('.doc') || name.endsWith('.docx')) return 'Document'
  if (name.endsWith('.xls') || name.endsWith('.xlsx')) return 'Grid'
  if (name.endsWith('.ppt') || name.endsWith('.pptx')) return 'DataAnalysis'
  return 'Paperclip'
}

function iconClass(att: Attachment): string {
  const mime = att.mime_type || ''
  const name = att.original_name.toLowerCase()
  if (mime.startsWith('image/')) return 'is-image'
  if (name.endsWith('.xls') || name.endsWith('.xlsx')) return 'is-excel'
  if (name.endsWith('.ppt') || name.endsWith('.pptx')) return 'is-ppt'
  if (mime.includes('pdf') || name.endsWith('.pdf')) return 'is-pdf'
  return ''
}

async function onDownload(att: Attachment) {
  downloading.value = att.id
  try {
    await downloadAttachment(att)
  } catch {
    // 错误提示已由 axios 拦截器统一处理
  } finally {
    downloading.value = null
  }
}
</script>

<style scoped>
.attachment-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.attachment-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid #e6ecec;
  border-radius: 10px;
  background: #fafcfc;
  transition: border-color 0.2s;
}

.attachment-item:hover {
  border-color: #9fccca;
}

.attachment-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.file-icon {
  font-size: 26px;
  color: #7a8a99;
  flex-shrink: 0;
}

.file-icon.is-image {
  color: #67c23a;
}

.file-icon.is-pdf {
  color: #f56c6c;
}

.file-icon.is-excel {
  color: #409e6c;
}

.file-icon.is-ppt {
  color: #e6a23c;
}

.attachment-info {
  min-width: 0;
}

.attachment-name {
  font-size: 14px;
  color: #2c3e50;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 420px;
}

.attachment-meta {
  font-size: 12px;
  color: #9aa7b3;
  margin-top: 2px;
}

.attachment-empty {
  color: #9aa7b3;
}

@media (max-width: 640px) {
  .attachment-name {
    max-width: 180px;
  }
}
</style>
