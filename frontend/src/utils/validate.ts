/** 附件校验（前端先行校验，后端仍会二次校验） */

export const ALLOWED_EXTENSIONS = [
  'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp',
  'pdf',
  'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
]

/** 默认值与后端 DEFAULT_* 一致（管理员可在系统配置中调整，前端展示默认限制） */
export const DEFAULT_MAX_FILE_SIZE_MB = 20
export const DEFAULT_MAX_FILES_PER_SUBMIT = 10

export function extOf(name: string): string {
  const idx = name.lastIndexOf('.')
  if (idx < 0 || idx === name.length - 1) return ''
  return name.slice(idx + 1).toLowerCase()
}

/** 校验单个文件；返回错误文案，合法返回 null */
export function validateFile(file: File, maxSizeMb: number = DEFAULT_MAX_FILE_SIZE_MB): string | null {
  const ext = extOf(file.name)
  if (!ext) return '无法识别文件类型'
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return `不支持的文件类型 .${ext}`
  }
  if (file.size > maxSizeMb * 1024 * 1024) {
    return `文件超过 ${maxSizeMb}MB 上限`
  }
  return null
}

/** 校验一批文件（数量 + 逐个校验），返回第一条错误文案，合法返回 null */
export function validateFiles(
  files: File[],
  maxCount: number = DEFAULT_MAX_FILES_PER_SUBMIT,
  maxSizeMb: number = DEFAULT_MAX_FILE_SIZE_MB,
): string | null {
  if (files.length > maxCount) {
    return `单次最多上传 ${maxCount} 个文件`
  }
  for (const f of files) {
    const err = validateFile(f, maxSizeMb)
    if (err) return `${f.name}：${err}`
  }
  return null
}
