<template>
  <div>
    <h2 class="page-title">IP 黑名单</h2>
    <div class="app-card">
      <div class="toolbar">
        <span class="muted">因请求频率过高被自动拉黑的 IP（最近 200 条）</span>
        <div class="spacer" />
        <el-button :icon="Refresh" @click="load">刷新</el-button>
      </div>

      <div class="table-wrap">
        <el-table v-loading="loading" :data="items">
          <el-table-column prop="ip" label="IP" min-width="150" />
          <el-table-column prop="reason" label="原因" min-width="200" show-overflow-tooltip />
          <el-table-column label="拉黑时间" width="170">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="解封时间" width="170">
            <template #default="{ row }">{{ formatDateTime(row.expires_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button text type="danger" size="small" :loading="removing === row.ip" @click="remove(row.ip)">解除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'

import * as adminApi from '@/api/admin'
import type { BlacklistItem } from '@/types'
import { formatDateTime } from '@/utils/format'

const items = ref<BlacklistItem[]>([])
const loading = ref(false)
const removing = ref('')

async function load() {
  loading.value = true
  try {
    const { data } = await adminApi.listBlacklist()
    items.value = data.items
  } catch {
    /* ignore */
  } finally {
    loading.value = false
  }
}

async function remove(ip: string) {
  try {
    await ElMessageBox.confirm(`确定将 IP ${ip} 移出黑名单？`, '解除拉黑', {
      confirmButtonText: '解除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  removing.value = ip
  try {
    await adminApi.removeBlacklist(ip)
    ElMessage.success(`IP ${ip} 已解除拉黑`)
    await load()
  } catch {
    /* ignore */
  } finally {
    removing.value = ''
  }
}

onMounted(load)
</script>
