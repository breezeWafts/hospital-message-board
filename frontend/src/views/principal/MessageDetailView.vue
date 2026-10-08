<template>
  <div v-loading="loading">
    <el-breadcrumb separator="/" class="crumb">
      <el-breadcrumb-item :to="{ name: 'principal-messages' }">留言列表</el-breadcrumb-item>
      <el-breadcrumb-item>留言 #{{ messageId }}</el-breadcrumb-item>
    </el-breadcrumb>

    <template v-if="detail">
      <!-- 基本信息 -->
      <div class="app-card">
        <div class="app-card-title">基本信息</div>
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

      <!-- 秘书审核信息 -->
      <div class="app-card">
        <div class="app-card-title">秘书审核</div>
        <template v-if="detail.secretary_review_result">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="审核结果">
              <el-tag :type="reviewResultType(detail.secretary_review_result)">{{ reviewResultText(detail.secretary_review_result) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="审核人">{{ detail.secretary_reviewer_name || '—' }}</el-descriptions-item>
            <el-descriptions-item label="审核时间">{{ formatDateTime(detail.secretary_reviewed_at) }}</el-descriptions-item>
            <el-descriptions-item label="审核意见">{{ detail.secretary_review_comment || '—' }}</el-descriptions-item>
          </el-descriptions>
        </template>
        <span v-else class="muted">秘书尚未审核</span>
      </div>

      <!-- 处理流程 -->
      <div class="app-card">
        <div class="app-card-title">处理流程</div>
        <WorkflowGraph :workflow="detail.workflow" />
      </div>

      <!-- 院长批示 / 待批示操作 -->
      <div class="app-card">
        <div class="app-card-title">院长批示</div>
        <template v-if="canInstruct">
          <el-input v-model="instruction" type="textarea" :rows="4" maxlength="5000" show-word-limit placeholder="请输入批示意见（将通知秘书分解任务）" />
          <div class="actions">
            <el-button type="primary" :loading="instructing" :disabled="instructing" @click="doInstruction">提交批示</el-button>
          </div>
        </template>
        <div v-else-if="detail.principal_instruction" class="instruction-box">{{ detail.principal_instruction }}</div>
        <span v-else class="muted">暂无批示（待秘书审核通过后批示）</span>
      </div>

      <!-- 留言附件（秘书审核通过后可见） -->
      <div class="app-card">
        <div class="app-card-title">留言附件</div>
        <AttachmentList :attachments="detail.attachments || []" />
        <div v-if="!(detail.attachments || []).length" class="muted">暂无附件（匿名留言附件在秘书审核通过后可见）</div>
      </div>

      <!-- 任务列表 -->
      <div class="app-card">
        <div class="app-card-title">部门任务</div>
        <el-table :data="detail.tasks">
          <el-table-column prop="id" label="任务编号" width="90" />
          <el-table-column prop="title" label="任务标题" min-width="180" show-overflow-tooltip />
          <el-table-column prop="department_name" label="部门" width="140" />
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="taskStatusType(row.status)">{{ taskStatusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="附件" width="90">
            <template #default="{ row }">{{ row.status === 'APPROVED' ? row.attachments.length : '审核后可见' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="90">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="goTask(row.id)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 最终确认 / 驳回 -->
      <div v-if="canConfirm" class="app-card">
        <div class="app-card-title">最终确认</div>
        <el-alert type="success" :closable="false" show-icon title="全部任务已通过秘书审核，请最终确认处理结果。" style="margin-bottom: 12px" />
        <div class="actions">
          <el-button type="primary" :loading="confirming" :disabled="confirming" @click="doConfirm">最终确认完成</el-button>
          <el-button type="danger" plain :loading="rejecting" :disabled="rejecting" @click="rejectVisible = true">驳回（退回部门处理）</el-button>
        </div>
      </div>

      <!-- 评价信息 -->
      <div class="app-card">
        <div class="app-card-title">匿名评价</div>
        <div v-if="detail.evaluations && detail.evaluations.length > 0">
          <div v-for="(e, i) in detail.evaluations" :key="i" class="eval-line">
            <el-tag :type="e.satisfied ? 'success' : 'warning'" size="small">{{ e.satisfied ? '满意' : '不满意' }}</el-tag>
            <span class="muted"> {{ formatDateTime(e.created_at) }}</span>
            <div v-if="e.content" class="review-comment">{{ e.content }}</div>
          </div>
        </div>
        <span v-else class="muted">暂无评价</span>
      </div>
    </template>

    <!-- 驳回原因弹窗 -->
    <el-dialog v-model="rejectVisible" title="驳回最终确认" width="480px">
      <el-form label-position="top">
        <el-form-item label="驳回原因（必填）">
          <el-input v-model="rejectComment" type="textarea" :rows="4" maxlength="2000" show-word-limit placeholder="请填写驳回原因，相关任务将退回部门重新处理" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectVisible = false">取消</el-button>
        <el-button type="danger" :loading="rejecting" :disabled="rejecting" @click="doReject">确认驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import * as principalApi from '@/api/principal'
import AttachmentList from '@/components/AttachmentList.vue'
import WorkflowGraph from '@/components/workflow/WorkflowGraph.vue'
import type { MessageDetail } from '@/types'
import { formatDateTime } from '@/utils/format'
import {
  messageStatusText,
  messageStatusType,
  reviewResultText,
  reviewResultType,
  taskStatusText,
  taskStatusType,
} from '@/utils/status'

const route = useRoute()
const router = useRouter()

const messageId = Number(route.params.id)
const detail = ref<MessageDetail | null>(null)
const loading = ref(false)

const instruction = ref('')
const instructing = ref(false)
const confirming = ref(false)
const rejecting = ref(false)
const rejectVisible = ref(false)
const rejectComment = ref('')

const canInstruct = computed(
  () => detail.value?.status === 'NEW' && detail.value.secretary_review_result === 'APPROVED',
)

const allApproved = computed(
  () =>
    (detail.value?.tasks?.length ?? 0) > 0 &&
    detail.value!.tasks.every((t) => t.status === 'APPROVED'),
)

const canConfirm = computed(() => detail.value?.status === 'REVIEWING' && allApproved.value)

async function load() {
  loading.value = true
  try {
    const { data } = await principalApi.getMessage(messageId)
    detail.value = data
    if (data.principal_instruction) instruction.value = data.principal_instruction
  } catch {
    /* 拦截器已提示 */
  } finally {
    loading.value = false
  }
}

async function doInstruction() {
  if (!instruction.value.trim()) {
    ElMessage.warning('请填写批示意见')
    return
  }
  instructing.value = true
  try {
    await principalApi.submitInstruction(messageId, instruction.value.trim())
    ElMessage.success('批示已提交，已通知秘书分解任务')
    await load()
  } catch {
    /* ignore */
  } finally {
    instructing.value = false
  }
}

async function doConfirm() {
  try {
    await ElMessageBox.confirm('确认该留言处理完成？确认后匿名用户可查询结果并进行评价。', '最终确认', {
      confirmButtonText: '确认完成',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  confirming.value = true
  try {
    await principalApi.confirmMessage(messageId)
    ElMessage.success('已完成最终确认')
    await load()
  } catch {
    /* ignore */
  } finally {
    confirming.value = false
  }
}

async function doReject() {
  if (!rejectComment.value.trim()) {
    ElMessage.warning('请填写驳回原因')
    return
  }
  rejecting.value = true
  try {
    await principalApi.rejectMessage(messageId, rejectComment.value.trim())
    ElMessage.success('已驳回，相关任务退回部门重新处理')
    rejectVisible.value = false
    rejectComment.value = ''
    await load()
  } catch {
    /* ignore */
  } finally {
    rejecting.value = false
  }
}

function goTask(taskId: number) {
  router.push({ name: 'principal-task-detail', params: { taskId } })
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

.instruction-box {
  background: #f5faf9;
  border: 1px solid #d8ebe9;
  border-radius: 8px;
  padding: 12px 14px;
  white-space: pre-wrap;
  line-height: 1.8;
}

.actions {
  display: flex;
  gap: 12px;
  margin-top: 12px;
}

.eval-line {
  padding: 6px 0;
}

.review-comment {
  margin-top: 4px;
  color: #5b6b7a;
  font-size: 13px;
  white-space: pre-wrap;
}
</style>
