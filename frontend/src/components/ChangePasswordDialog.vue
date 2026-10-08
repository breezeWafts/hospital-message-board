<template>
  <el-dialog
    :model-value="modelValue"
    :close-on-click-modal="!forced"
    :close-on-press-escape="!forced"
    :show-close="!forced"
    title="修改密码"
    width="480px"
    @update:model-value="onVisibleChange"
  >
    <el-alert
      v-if="forced"
      type="warning"
      :closable="false"
      show-icon
      title="首次登录或密码已被重置，请先修改密码后再使用系统"
      style="margin-bottom: 14px"
    />
    <ChangePasswordForm @success="onSuccess" />
  </el-dialog>
</template>

<script setup lang="ts">
import ChangePasswordForm from './ChangePasswordForm.vue'

const props = defineProps<{
  modelValue: boolean
  /** 强制模式（首次登录/重置后）：不可关闭 */
  forced?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'success'): void
}>()

function onVisibleChange(value: boolean) {
  if (props.forced && !value) return
  emit('update:modelValue', value)
}

function onSuccess() {
  emit('success')
  if (!props.forced) emit('update:modelValue', false)
}
</script>
