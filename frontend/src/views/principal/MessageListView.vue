<template>
  <div>
    <h2 class="page-title">留言列表</h2>

    <!-- 视图选项卡 -->
    <el-tabs v-model="view" class="view-tabs" @tab-change="onTabChange">
      <el-tab-pane label="待批示" name="instruction" />
      <el-tab-pane label="待最终确认" name="confirm" />
      <el-tab-pane label="全部" name="all" />
    </el-tabs>

    <div class="app-card">
      <div class="toolbar">
        <el-select v-model="status" placeholder="全部状态" clearable :disabled="view !== 'all'" style="width: 160px" @change="onFilterChange">
          <el-option v-for="o in MESSAGE_STATUS_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-input v-model="search" placeholder="搜索标题/内容" clearable style="width: 220px" @keyup.enter="onFilterChange" @clear="onFilterChange" />
        <el-select v-model="sort" style="width: 170px" @change="onFilterChange">
          <el-option label="按提交时间倒序" value="created_at_desc" />
          <el-option label="按提交时间正序" value="created_at_asc" />
          <el-option label="按更新时间倒序" value="updated_at_desc" />
          <el-option label="按编号倒序" value="id_desc" />
        </el-select>
        <el-button type="primary" @click="onFilterChange">查询</el-button>
      </div>

      <div class="table-wrap">
        <el-table v-loading="loading" :data="items" @row-click="goDetail" row-class-name="clickable-row">
          <el-table-column prop="id" label="编号" width="70" />
          <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
          <el-table-column label="状态" width="140">
            <template #default="{ row }">
              <el-tag :type="messageStatusType(row.status)">{{ messageStatusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="task_count" label="任务数" width="80" />
          <el-table-column prop="department_names" label="涉及部门" min-width="160" show-overflow-tooltip />
          <el-table-column label="提交时间" width="160">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="80" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click.stop="goDetail(row)">查看</el-button>
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

import * as principalApi from '@/api/principal'
import type { MessageListItem } from '@/types'
import { formatDateTime } from '@/utils/format'
import { MESSAGE_STATUS_OPTIONS, messageStatusText, messageStatusType } from '@/utils/status'

const router = useRouter()

const view = ref<'instruction' | 'confirm' | 'all'>('instruction')
const status = ref('')
const search = ref('')
const sort = ref('created_at_desc')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const items = ref<MessageListItem[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await principalApi.listMessages({
      view: view.value,
      status: status.value || undefined,
      search: search.value || undefined,
      page: page.value,
      page_size: pageSize.value,
      sort: sort.value,
    })
    items.value = data.items
    total.value = data.total
  } catch {
    /* 拦截器已提示 */
  } finally {
    loading.value = false
  }
}

function onTabChange() {
  status.value = ''
  page.value = 1
  void load()
}

function onFilterChange() {
  page.value = 1
  void load()
}

function onSizeChange() {
  page.value = 1
  void load()
}

function goDetail(row: MessageListItem) {
  router.push({ name: 'principal-message-detail', params: { id: row.id } })
}

onMounted(load)
</script>

<style scoped>
.view-tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
}

:deep(.clickable-row) {
  cursor: pointer;
}
</style>
