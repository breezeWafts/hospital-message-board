<template>
  <PublicHeader>
    <div class="evaluate-page">
      <el-result
        v-if="!hasCaptcha"
        icon="warning"
        title="无法评价"
        sub-title="未找到查询验证码，请先通过“进度查询”验证身份后再进入评价页。"
      >
        <template #extra>
          <el-button type="primary" @click="$router.push({ name: 'query' })">去查询</el-button>
        </template>
      </el-result>

      <div v-else class="app-card">
        <div class="app-card-title">满意度评价 · 留言 #{{ messageId }}</div>
        <el-form label-position="top">
          <el-form-item label="您对本次处理结果是否满意？">
            <el-radio-group v-model="form.satisfied">
              <el-radio :value="true" size="large">满意</el-radio>
              <el-radio :value="false" size="large">不满意</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="评价内容（可选）">
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="4"
              maxlength="2000"
              show-word-limit
              placeholder="欢迎留下您的宝贵意见"
            />
          </el-form-item>
          <el-button type="primary" :loading="submitting" :disabled="submitting" @click="submit">
            提交评价
          </el-button>
          <el-button @click="$router.push({ name: 'query' })">返回查询</el-button>
        </el-form>
      </div>

      <el-result
        v-if="done"
        :icon="doneSatisfied ? 'success' : 'warning'"
        :title="doneSatisfied ? '评价成功' : '已收到您的评价'"
        :sub-title="doneSatisfied ? '感谢您的认可，该留言已归档。' : '感谢您的反馈，我们会继续改进。'"
      >
        <template #extra>
          <el-button type="primary" @click="$router.push({ name: 'query' })">返回查询</el-button>
          <el-button @click="$router.push({ name: 'submit' })">返回首页</el-button>
        </template>
      </el-result>
    </div>
  </PublicHeader>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import * as anonymousApi from '@/api/anonymous'
import { extractApiError } from '@/api/http'
import PublicHeader from '@/components/PublicHeader.vue'

const route = useRoute()

const messageId = computed(() => Number(route.params.id) || 0)
const captcha = ref('')
const hasCaptcha = computed(() => !!captcha.value)

const form = reactive({ satisfied: true, content: '' })
const submitting = ref(false)
const done = ref(false)
const doneSatisfied = ref(true)

onMounted(() => {
  const key = `hmb_eval_captcha_${messageId.value}`
  captcha.value = sessionStorage.getItem(key) || ''
})

async function submit() {
  if (submitting.value || !messageId.value) return
  submitting.value = true
  try {
    const { data } = await anonymousApi.evaluateMessage(
      messageId.value,
      captcha.value,
      form.satisfied,
      form.content.trim() || undefined,
    )
    done.value = true
    doneSatisfied.value = form.satisfied
    if (data.status === 'ARCHIVED') {
      sessionStorage.removeItem(`hmb_eval_captcha_${messageId.value}`)
    }
    ElMessage.success(data.status === 'ARCHIVED' ? '评价成功，留言已归档' : '已收到您的评价')
  } catch (e) {
    ElMessage.error(extractApiError(e).message)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.evaluate-page {
  max-width: 680px;
  margin: 0 auto;
}
</style>
