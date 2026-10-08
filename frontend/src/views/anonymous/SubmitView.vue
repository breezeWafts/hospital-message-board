<template>
  <PublicHeader>
    <div class="submit-page">
      <div class="page-hero">
        <h1 class="hero-title">匿名留言</h1>
        <p class="hero-sub">
          无需注册登录，写下您对医院的意见与建议。提交后请妥善保管<strong>留言编号</strong>与<strong>查询验证码</strong>。
        </p>
      </div>

      <div class="app-card">
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <el-form-item label="留言标题" prop="title">
            <el-input
              v-model="form.title"
              maxlength="200"
              show-word-limit
              placeholder="请简要概括您的留言内容（200 字以内）"
            />
          </el-form-item>

          <el-form-item label="留言内容" prop="content">
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="8"
              maxlength="20000"
              show-word-limit
              placeholder="请详细描述您的意见、建议或反映的问题（20000 字以内）"
            />
          </el-form-item>

          <el-form-item label="附件（可选）">
            <AttachmentUploader v-model:files="form.files" />
          </el-form-item>

          <div class="submit-actions">
            <el-button type="primary" size="large" :loading="submitting" :disabled="submitting" @click="submit">
              {{ submitting ? '提交中…' : '匿名提交' }}
            </el-button>
            <el-button size="large" @click="reset">清空重填</el-button>
          </div>

          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="我们承诺对您的身份信息严格保密，留言全程匿名，无需提供任何个人身份信息。"
          />
        </el-form>
      </div>
    </div>
  </PublicHeader>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

import * as anonymousApi from '@/api/anonymous'
import { extractApiError } from '@/api/http'
import AttachmentUploader from '@/components/AttachmentUploader.vue'
import PublicHeader from '@/components/PublicHeader.vue'
import { validateFiles } from '@/utils/validate'

const router = useRouter()
const formRef = ref<FormInstance>()

const form = reactive({
  title: '',
  content: '',
  files: [] as File[],
})

const rules: FormRules = {
  title: [
    { required: true, message: '请输入留言标题', trigger: 'blur' },
    { max: 200, message: '标题不能超过 200 字', trigger: 'blur' },
  ],
  content: [
    { required: true, message: '请输入留言内容', trigger: 'blur' },
    { max: 20000, message: '内容不能超过 20000 字', trigger: 'blur' },
  ],
}

const submitting = ref(false)
const progress = ref(0)

async function submit() {
  if (submitting.value) return // 防重复提交
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  const fileErr = validateFiles(form.files)
  if (fileErr) {
    ElMessage.error(fileErr)
    return
  }

  submitting.value = true
  progress.value = 0
  const fd = new FormData()
  fd.append('title', form.title)
  fd.append('content', form.content)
  form.files.forEach((f) => fd.append('attachments', f))

  try {
    const { data } = await anonymousApi.submitMessage(fd, (p) => (progress.value = p))
    // 结果写入 sessionStorage 兜底 + history.state 传递
    sessionStorage.setItem('hmb_submit_result', JSON.stringify(data))
    router.push({ name: 'submit-success', state: data })
  } catch (e) {
    ElMessage.error(extractApiError(e).message)
  } finally {
    submitting.value = false
  }
}

function reset() {
  form.title = ''
  form.content = ''
  form.files = []
}
</script>

<style scoped>
.page-hero {
  text-align: center;
  padding: 8px 0 20px;
}

.hero-title {
  font-size: 26px;
  color: #0b615f;
  margin: 0 0 8px;
}

.hero-sub {
  color: #7a8a99;
  font-size: 14px;
  margin: 0;
  line-height: 1.8;
}

.submit-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
</style>
