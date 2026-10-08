<template>
  <div>
    <h2 class="page-title">系统配置</h2>
    <div class="app-card" v-loading="loading">
      <div class="app-card-title">运行参数</div>
      <el-form :model="configs" label-width="240px" label-position="left" class="config-form">
        <el-form-item v-for="c in CONFIG_FIELDS" :key="c.key" :label="c.label">
          <el-input-number v-model="configs[c.key]" :min="1" :max="c.max" :step="1" style="width: 200px" />
          <span class="muted unit">{{ c.unit }}</span>
          <div class="muted desc">{{ c.desc }}</div>
        </el-form-item>
      </el-form>
      <div class="actions">
        <el-button type="primary" :loading="saving" :disabled="saving" @click="save">保存配置</el-button>
        <el-button @click="load">重置为当前值</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import * as adminApi from '@/api/admin'

interface ConfigField {
  key: string
  label: string
  unit: string
  desc: string
  max: number
}

const CONFIG_FIELDS: ConfigField[] = [
  { key: 'max_file_size_mb', label: '单个附件大小上限', unit: 'MB', desc: '超过该大小的附件将被拒绝', max: 200 },
  { key: 'max_files_per_submit', label: '单次提交附件数量上限', unit: '个', desc: '匿名提交与部门提交共同生效', max: 50 },
  { key: 'captcha_ttl_days', label: '查询验证码有效期', unit: '天', desc: '过期后需联系管理员处理', max: 365 },
  { key: 'captcha_max_attempts', label: '验证码最大错误次数', unit: '次', desc: '超过后验证码将被锁定', max: 100 },
  { key: 'captcha_lock_days', label: '验证码锁定时长', unit: '天', desc: '锁定期间仅管理员可解除', max: 365 },
  { key: 'login_max_attempts', label: '登录最大失败次数', unit: '次', desc: '超过后账号将被锁定', max: 100 },
  { key: 'login_lock_minutes', label: '登录锁定时长', unit: '分钟', desc: '锁定到期后自动解锁', max: 1440 * 7 },
  { key: 'rate_limit_max_requests', label: '限流：窗口内最大请求数', unit: '次', desc: '超过阈值将触发限流', max: 100000 },
  { key: 'rate_limit_window_seconds', label: '限流：统计窗口', unit: '秒', desc: '滑动窗口长度', max: 86400 },
  { key: 'blacklist_ban_seconds', label: '自动拉黑时长', unit: '秒', desc: '触发限流后 IP 被封禁的时长', max: 86400 * 30 },
  { key: 'anon_submit_cooldown_seconds', label: '匿名提交冷却时间', unit: '秒', desc: '同一 IP 两次提交的最小间隔', max: 86400 },
]

const configs = reactive<Record<string, number>>({})
const loading = ref(false)
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await adminApi.getConfigs()
    for (const c of CONFIG_FIELDS) {
      configs[c.key] = Number(data.configs[c.key]) || 0
    }
  } catch {
    /* ignore */
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const payload: Record<string, string> = {}
    for (const c of CONFIG_FIELDS) {
      payload[c.key] = String(configs[c.key])
    }
    await adminApi.updateConfigs(payload)
    ElMessage.success('配置已保存并生效')
    await load()
  } catch {
    /* ignore */
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.config-form {
  max-width: 760px;
}

.unit {
  margin-left: 10px;
}

.desc {
  width: 100%;
  line-height: 1.5;
}

.actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}
</style>
