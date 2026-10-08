<template>
  <div>
    <h2 class="page-title">日志查询</h2>
    <div class="app-card">
      <div class="toolbar">
        <el-select v-model="filters.action" placeholder="全部动作" clearable filterable style="width: 180px">
          <el-option v-for="a in AUDIT_ACTIONS" :key="a" :label="actionText(a)" :value="a" />
        </el-select>
        <el-select v-model="filters.role" placeholder="全部角色" clearable style="width: 140px">
          <el-option v-for="(label, value) in ROLE_TEXT" :key="value" :label="label" :value="value" />
        </el-select>
        <el-input v-model="filters.operator" placeholder="操作人" clearable style="width: 150px" />
        <el-input-number v-model="filters.message_id" :min="1" :controls="false" placeholder="留言编号" style="width: 130px" />
        <el-input-number v-model="filters.task_id" :min="1" :controls="false" placeholder="任务编号" style="width: 130px" />
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 260px"
        />
        <el-select v-model="filters.sort" style="width: 150px">
          <el-option label="按时间倒序" value="created_at_desc" />
          <el-option label="按时间正序" value="created_at_asc" />
          <el-option label="按 ID 倒序" value="id_desc" />
        </el-select>
        <el-button type="primary" @click="onSearch">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </div>

      <div class="table-wrap">
        <el-table v-loading="loading" :data="items">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column label="时间" width="160">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="动作" width="140">
            <template #default="{ row }">{{ actionText(row.action) }}</template>
          </el-table-column>
          <el-table-column prop="operator_name" label="操作人" min-width="120" show-overflow-tooltip />
          <el-table-column label="角色" width="100">
            <template #default="{ row }">{{ roleText(row.role) }}</template>
          </el-table-column>
          <el-table-column prop="ip" label="IP" width="130" />
          <el-table-column label="留言" width="80">
            <template #default="{ row }">{{ row.message_id ?? '—' }}</template>
          </el-table-column>
          <el-table-column label="任务" width="80">
            <template #default="{ row }">{{ row.task_id ?? '—' }}</template>
          </el-table-column>
          <el-table-column label="状态变化" width="150">
            <template #default="{ row }">
              <span v-if="row.before_status || row.after_status">
                {{ row.before_status || '—' }} → {{ row.after_status || '—' }}
              </span>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column label="UA" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">{{ row.ua || '—' }}</template>
          </el-table-column>
        </el-table>
      </div>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @current-change="load"
          @size-change="onSizeChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import * as adminApi from '@/api/admin'
import type { AuditLog } from '@/types'
import { formatDateTime } from '@/utils/format'
import { AUDIT_ACTIONS, ROLE_TEXT, actionText, roleText } from '@/utils/status'

const filters = reactive({
  action: '',
  role: '',
  operator: '',
  message_id: undefined as number | undefined,
  task_id: undefined as number | undefined,
  sort: 'created_at_desc',
})

const dateRange = ref<[string, string] | null>(null)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const items = ref<AuditLog[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await adminApi.listLogs({
      action: filters.action || undefined,
      role: filters.role || undefined,
      operator: filters.operator.trim() || undefined,
      message_id: filters.message_id || undefined,
      task_id: filters.task_id || undefined,
      date_from: dateRange.value?.[0],
      date_to: dateRange.value?.[1],
      sort: filters.sort,
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

function onSearch() {
  page.value = 1
  void load()
}

function onSizeChange() {
  page.value = 1
  void load()
}

function reset() {
  filters.action = ''
  filters.role = ''
  filters.operator = ''
  filters.message_id = undefined
  filters.task_id = undefined
  filters.sort = 'created_at_desc'
  dateRange.value = null
  page.value = 1
  void load()
}

onMounted(load)
</script>
