<template>
  <div v-loading="loading">
    <el-breadcrumb separator="/" class="crumb">
      <el-breadcrumb-item :to="{ name: 'secretary-messages' }">留言列表</el-breadcrumb-item>
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
          <el-descriptions-item label="提交 IP">{{ detail.submit_ip || '—' }}</el-descriptions-item>
          <el-descriptions-item label="验证码错误次数">{{ detail.captcha_attempts ?? 0 }}</el-descriptions-item>
          <el-descriptions-item label="验证码锁定至">{{ formatDateTime(detail.captcha_locked_until) }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ formatDateTime(detail.completed_at) }}</el-descriptions-item>
        </el-descriptions>
        <el-divider content-position="left">留言内容</el-divider>
        <div class="content-box">{{ detail.content }}</div>
        <div v-if="detail.submit_ua" class="muted" style="margin-top: 8px">UA：{{ detail.submit_ua }}</div>
      </div>

      <!-- 审核操作 -->
      <div v-if="canReview" class="app-card review-card">
        <div class="app-card-title">留言审核</div>
        <el-input v-model="reviewComment" type="textarea" :rows="3" maxlength="2000" show-word-limit placeholder="审核意见（驳回/拒绝时必填）" />
        <div class="actions">
          <el-button type="success" :loading="reviewing" :disabled="reviewing" @click="doReview('APPROVED')">审核通过</el-button>
          <el-button type="danger" plain :loading="reviewing" :disabled="reviewing" @click="doReview('REJECTED')">驳回</el-button>
          <el-button type="warning" plain :loading="reviewing" :disabled="reviewing" @click="doReview('REFUSED')">拒绝受理</el-button>
        </div>
      </div>

      <!-- 秘书审核结果 -->
      <div v-else class="app-card">
        <div class="app-card-title">秘书审核</div>
        <el-descriptions v-if="detail.secretary_review_result" :column="2" border>
          <el-descriptions-item label="审核结果">
            <el-tag :type="reviewResultType(detail.secretary_review_result)">{{ reviewResultText(detail.secretary_review_result) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="审核人">{{ detail.secretary_reviewer_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="审核时间">{{ formatDateTime(detail.secretary_reviewed_at) }}</el-descriptions-item>
          <el-descriptions-item label="审核意见">{{ detail.secretary_review_comment || '—' }}</el-descriptions-item>
        </el-descriptions>
        <span v-else class="muted">尚未审核</span>
      </div>

      <!-- 院长批示 -->
      <div class="app-card">
        <div class="app-card-title">院长批示</div>
        <div v-if="detail.principal_instruction" class="instruction-box">{{ detail.principal_instruction }}</div>
        <span v-else class="muted">暂无批示</span>
      </div>

      <!-- 处理流程 -->
      <div class="app-card">
        <div class="app-card-title">处理流程</div>
        <WorkflowGraph :workflow="detail.workflow" />
      </div>

      <!-- 留言附件 -->
      <div class="app-card">
        <div class="app-card-title">留言附件</div>
        <AttachmentList :attachments="detail.attachments || []" />
      </div>

      <!-- 分派任务（PENDING） -->
      <div v-if="canAssign" class="app-card">
        <div class="app-card-title">分派部门任务</div>
        <div v-for="(row, i) in assignRows" :key="i" class="assign-row">
          <el-select v-model="row.department_id" placeholder="选择部门" style="width: 170px">
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
          <el-input v-model="row.title" placeholder="任务标题" style="width: 220px" maxlength="200" />
          <el-input v-model="row.content" placeholder="任务内容说明（可选）" style="flex: 1" maxlength="5000" />
          <el-button text type="danger" :icon="Delete" @click="assignRows.splice(i, 1)" :disabled="assignRows.length <= 1" />
        </div>
        <div class="actions">
          <el-button :icon="Plus" @click="assignRows.push({ department_id: null, title: '', content: '' })">添加任务</el-button>
          <el-button type="primary" :loading="assigning" :disabled="assigning" @click="doAssign">分派</el-button>
        </div>
      </div>

      <!-- 任务列表与逐任务审核 -->
      <div class="app-card">
        <div class="app-card-title">部门任务</div>
        <el-table v-if="detail.tasks.length > 0" :data="detail.tasks">
          <el-table-column prop="id" label="编号" width="70" />
          <el-table-column prop="title" label="任务标题" min-width="160" show-overflow-tooltip />
          <el-table-column prop="department_name" label="部门" width="130" />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="taskStatusType(row.status)">{{ taskStatusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="上次审核" width="110">
            <template #default="{ row }">
              <el-tag v-if="row.last_review_result" :type="reviewResultType(row.last_review_result)" size="small">
                {{ reviewResultText(row.last_review_result) }}
              </el-tag>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="goTask(row.id)">详情</el-button>
              <template v-if="row.status === 'REVIEWING'">
                <el-button text type="success" size="small" :loading="taskReviewing === row.id" @click="openTaskReview(row, 'APPROVED')">通过</el-button>
                <el-button text type="danger" size="small" :loading="taskReviewing === row.id" @click="openTaskReview(row, 'REJECTED')">驳回</el-button>
              </template>
            </template>
          </el-table-column>
        </el-table>
        <span v-else class="muted">暂无任务（院长批示后可分派）</span>
      </div>

      <!-- 归档 -->
      <div v-if="canArchive" class="app-card">
        <div class="app-card-title">归档</div>
        <el-button type="primary" :loading="archiving" :disabled="archiving" @click="doArchive">归档该留言</el-button>
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

    <!-- 任务审核弹窗（驳回必填批注） -->
    <el-dialog v-model="taskReviewVisible" :title="`任务审核：${taskReviewTarget?.title ?? ''}`" width="480px">
      <el-alert v-if="taskReviewResult === 'REJECTED'" type="warning" :closable="false" show-icon title="驳回后任务将退回部门重新处理，请务必填写批注。" style="margin-bottom: 12px" />
      <el-form label-position="top">
        <el-form-item label="审核意见">
          <el-input v-model="taskReviewComment" type="textarea" :rows="3" maxlength="2000" show-word-limit placeholder="通过可不填；驳回必填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="taskReviewVisible = false">取消</el-button>
        <el-button type="primary" :loading="taskReviewing !== null" :disabled="taskReviewing !== null" @click="doTaskReview">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Plus } from '@element-plus/icons-vue'

import * as secretaryApi from '@/api/secretary'
import AttachmentList from '@/components/AttachmentList.vue'
import WorkflowGraph from '@/components/workflow/WorkflowGraph.vue'
import type { Department, MessageDetail, Task } from '@/types'
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

// ---------- 留言审核 ----------
const canReview = computed(() => detail.value?.status === 'NEW' && !detail.value.secretary_review_result)
const reviewComment = ref('')
const reviewing = ref(false)

async function doReview(result: 'APPROVED' | 'REJECTED' | 'REFUSED') {
  if (result !== 'APPROVED' && !reviewComment.value.trim()) {
    ElMessage.warning('驳回/拒绝必须填写原因')
    return
  }
  if (result !== 'APPROVED') {
    try {
      await ElMessageBox.confirm(`确定${result === 'REJECTED' ? '驳回' : '拒绝受理'}该留言？`, '确认操作', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      })
    } catch {
      return
    }
  }
  reviewing.value = true
  try {
    await secretaryApi.reviewMessage(messageId, result, reviewComment.value.trim() || undefined)
    ElMessage.success('审核完成')
    reviewComment.value = ''
    await load()
  } catch {
    /* ignore */
  } finally {
    reviewing.value = false
  }
}

// ---------- 分派任务 ----------
const canAssign = computed(() => detail.value?.status === 'PENDING')
const departments = ref<Department[]>([])
const assignRows = reactive<{ department_id: number | null; title: string; content: string }[]>([
  { department_id: null, title: '', content: '' },
])
const assigning = ref(false)

async function loadDepartments() {
  try {
    const { data } = await secretaryApi.listDepartments()
    departments.value = data
  } catch {
    departments.value = []
  }
}

async function doAssign() {
  for (const row of assignRows) {
    if (!row.department_id) {
      ElMessage.warning('请为每行选择部门')
      return
    }
    if (!row.title.trim()) {
      ElMessage.warning('请填写任务标题')
      return
    }
  }
  assigning.value = true
  try {
    const { data } = await secretaryApi.assignTasks(
      messageId,
      assignRows.map((r) => ({
        department_id: r.department_id as number,
        title: r.title.trim(),
        content: r.content.trim() || undefined,
      })),
    )
    ElMessage.success(`已分派 ${data.task_count} 个任务`)
    assignRows.splice(0, assignRows.length, { department_id: null, title: '', content: '' })
    await load()
  } catch {
    /* ignore */
  } finally {
    assigning.value = false
  }
}

// ---------- 逐任务审核 ----------
const taskReviewVisible = ref(false)
const taskReviewTarget = ref<Task | null>(null)
const taskReviewResult = ref<'APPROVED' | 'REJECTED'>('APPROVED')
const taskReviewComment = ref('')
const taskReviewing = ref<number | null>(null)

function openTaskReview(task: Task, result: 'APPROVED' | 'REJECTED') {
  taskReviewTarget.value = task
  taskReviewResult.value = result
  taskReviewComment.value = ''
  taskReviewVisible.value = true
}

async function doTaskReview() {
  if (!taskReviewTarget.value) return
  if (taskReviewResult.value === 'REJECTED' && !taskReviewComment.value.trim()) {
    ElMessage.warning('驳回必须填写批注')
    return
  }
  taskReviewing.value = taskReviewTarget.value.id
  try {
    await secretaryApi.reviewTask(
      taskReviewTarget.value.id,
      taskReviewResult.value,
      taskReviewComment.value.trim() || undefined,
    )
    ElMessage.success('任务审核完成')
    taskReviewVisible.value = false
    await load()
  } catch {
    /* ignore */
  } finally {
    taskReviewing.value = null
  }
}

// ---------- 归档 ----------
const canArchive = computed(() => detail.value?.status === 'COMPLETED' || detail.value?.status === 'REJECTED')
const archiving = ref(false)

async function doArchive() {
  try {
    await ElMessageBox.confirm('归档后留言进入终态（匿名端显示已归档）。确定归档？', '归档', {
      confirmButtonText: '归档',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  archiving.value = true
  try {
    await secretaryApi.archiveMessage(messageId)
    ElMessage.success('已归档')
    await load()
  } catch {
    /* ignore */
  } finally {
    archiving.value = false
  }
}

function goTask(taskId: number) {
  router.push({ name: 'secretary-task-detail', params: { taskId } })
}

async function load() {
  loading.value = true
  try {
    const { data } = await secretaryApi.getMessage(messageId)
    detail.value = data
  } catch {
    /* ignore */
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
  void loadDepartments()
})
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
  flex-wrap: wrap;
}

.assign-row {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.review-card {
  border-left: 4px solid #e6a23c;
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
