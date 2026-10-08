<template>
  <div>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" label-position="left">
      <el-form-item v-if="!isOAuth" label="原密码" prop="old_password">
        <el-input v-model="form.old_password" type="password" show-password placeholder="请输入原密码" autocomplete="current-password" />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input v-model="form.new_password" type="password" show-password placeholder="至少 8 位，且同时包含字母和数字" autocomplete="new-password" />
      </el-form-item>
      <el-form-item label="确认新密码" prop="confirm_password">
        <el-input v-model="form.confirm_password" type="password" show-password placeholder="请再次输入新密码" autocomplete="new-password" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="submitting" @click="submit">确认修改</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

import * as authApi from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const emit = defineEmits<{ (e: 'success'): void }>()

const auth = useAuthStore()
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

/** 统一认证用户无本地密码，后端跳过原密码校验，仅需 schema 非空 */
const isOAuth = computed(() => auth.user?.auth_source === 'oauth2')

const rules = computed<FormRules>(() => ({
  old_password: isOAuth.value
    ? []
    : [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 位', trigger: 'blur' },
    {
      validator: (_rule: unknown, value: string, callback: (error?: Error) => void) => {
        if (/[a-zA-Z]/.test(value) && /\d/.test(value)) callback()
        else callback(new Error('密码必须同时包含字母和数字'))
      },
      trigger: 'blur',
    },
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule: unknown, value: string, callback: (error?: Error) => void) => {
        if (value === form.new_password) callback()
        else callback(new Error('两次输入的密码不一致'))
      },
      trigger: 'blur',
    },
  ],
}))

async function submit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  submitting.value = true
  try {
    await authApi.changePassword({
      old_password: isOAuth.value && !form.old_password ? '-' : form.old_password,
      new_password: form.new_password,
    })
    await auth.fetchMe()
    ElMessage.success('密码修改成功')
    form.old_password = ''
    form.new_password = ''
    form.confirm_password = ''
    emit('success')
  } catch {
    // 错误提示已由拦截器统一处理
  } finally {
    submitting.value = false
  }
}
</script>
