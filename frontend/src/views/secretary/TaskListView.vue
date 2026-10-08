<template>
  <div>
    <h2 class="page-title">任务列表</h2>
    <div class="app-card">
      <div class="toolbar">
        <el-select v-model="status" placeholder="全部状态" clearable style="width: 160px" @change="onFilterChange">
          <el-option v-for="o in TASK_STATUS_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-input-number v-model="messageId" :min="1" :controls="false" placeholder="留言编号筛选" style="width: 160px" @change="onFilterChange" />
        <el-button type="primary" @click="onFilterChange">查询</el-button>
      </div>

      <div class="table-wrap">
        <el-table v-loading="loading" :data="items" @row-click="goDetail" row-class-name="clickable-row">
          <el-table-column prop="id" label="任务编号" width="90" />
          <el-table-column label="所属留言" width="150">
            <template #default="{ row }">#{{ row.message_id }} {{ row.message_title }}</template>
          </el-table-column>
          <el-table-column prop="title" label="任务标题" min-width="180" show-overflow-tooltip />
          <el-table-column prop="department_name" label="部门" width="140" />
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="taskStatusType(row.status)">{{ taskStatusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="提交时间" width="160">
            <template #default="{ row }">{{ formatDateTime(row.submitted_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="80" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click.stop="goDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="load"
          @size-change="onSizeChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import * as secretaryApi from '@/api/secretary'
import type { TaskListItem } from '@/types'
import { formatDateTime } from '@/utils/format'
import { TASK_STATUS_OPTIONS, taskStatusText, taskStatusType } from '@/utils/status'

const router = useRouter()

const status = ref('')
const messageId = ref<number | undefined>(undefined)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const items = ref<TaskListItem[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await secretaryApi.listTasks({
      status: status.value || undefined,
      message_id: messageId.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    items.value = data.items
    total.value = data.total
  } catch {
    /* ignore */
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  page.value = 1
  void load()
}

function onSizeChange() {
  page.value = 1
  void load()
}

function goDetail(row: TaskListItem) {
  router.push({ name: 'secretary-task-detail', params: { taskId: row.id } })
}

onMounted(load)
</script>

<style scoped>
:deep(.clickable-row) {
  cursor: pointer;
}
</style>
