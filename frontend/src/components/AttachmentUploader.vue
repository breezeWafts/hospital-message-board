<template>
  <div>
    <el-upload
      ref="uploadRef"
      drag
      multiple
      :auto-upload="false"
      :limit="maxFiles"
      :accept="accept"
      :file-list="fileList"
      :on-change="onChange"
      :on-remove="onRemove"
      :on-exceed="onExceed"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">将附件拖到此处，或<em>点击选择</em></div>
    </el-upload>
    <div class="upload-tip">
      支持 jpg / jpeg / png / gif / bmp / webp / pdf / doc / docx / xls / xlsx / ppt / pptx；
      单文件不超过 {{ maxSizeMb }}MB，单次最多 {{ maxFiles }} 个。
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile, UploadInstance, UploadUserFile } from 'element-plus'

import { DEFAULT_MAX_FILE_SIZE_MB, validateFile } from '@/utils/validate'

const props = defineProps<{
  files: File[]
  /** 单文件大小上限 MB（默认 20） */
  maxSizeMb?: number
  /** 单次数量上限（默认 10） */
  maxFiles?: number
}>()

const emit = defineEmits<{
  (e: 'update:files', files: File[]): void
}>()

const accept = '.jpg,.jpeg,.png,.gif,.bmp,.webp,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx'
const maxSizeMb = props.maxSizeMb ?? DEFAULT_MAX_FILE_SIZE_MB
const maxFiles = props.maxFiles ?? 10

const uploadRef = ref<UploadInstance>()
const fileList = ref<UploadUserFile[]>([])

function sync() {
  emit(
    'update:files',
    fileList.value.map((f) => (f.raw ? (f.raw as File) : null)).filter((f): f is File => !!f),
  )
}

function onExceed() {
  ElMessage.warning(`单次最多上传 ${maxFiles} 个文件`)
}

function onChange(file: UploadFile) {
  const raw = file.raw
  if (!raw) return
  const err = validateFile(raw as File, maxSizeMb)
  if (err) {
    ElMessage.error(`${raw.name}：${err}`)
    fileList.value = fileList.value.filter((f) => f.uid !== file.uid)
  }
  sync()
}

function onRemove() {
  sync()
}

defineExpose({ clear: () => (fileList.value = []) })
</script>

<style scoped>
.upload-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #9aa7b3;
  line-height: 1.6;
}
</style>
