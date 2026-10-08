<template>
  <div>
    <h2 class="page-title">验证码重置</h2>
    <div class="app-card reset-card">
      <div class="app-card-title">解除查询验证码锁定</div>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="仅解除锁定，验证码不变"
        description="当匿名用户因验证码错误次数过多被锁定时，可输入留言编号解除锁定。原验证码保持不变，用户可继续使用原验证码查询。"
        style="margin-bottom: 16px"
      />
      <el-form :inline="true">
        <el-form-item label="留言编号">
          <el-input-number v-model="messageId" :min="1" :controls="false" style="width: 200px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" :disabled="submitting" @click="submit">解除锁定</el-button>
        </el-form-item>
      </el-form>
      <el-alert v-if="result" type="success" show-icon :closable="false" :title="`留言 #${result.message_id} 的验证码锁定已解除，验证码保持不变。`" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

import * as adminApi from '@/api/admin'
import { extractApiError } from '@/api/http'

const messageId = ref<number | null>(null)
const submitting = ref(false)
const result = ref<{ ok: boolean; message_id: number } | null>(null)

async function submit() {
  if (submitting.value) return
  if (!messageId.value) {
    ElMessage.warning('请输入留言编号')
    return
  }
  submitting.value = true
  result.value = null
  try {
    const { data } = await adminApi.resetCaptcha(messageId.value)
    result.value = data
    ElMessage.success(`留言 #${data.message_id} 的验证码锁定已解除（验证码不变）`)
  } catch (e) {
    ElMessage.error(extractApiError(e).message)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.reset-card {
  max-width: 680px;
}
</style>
