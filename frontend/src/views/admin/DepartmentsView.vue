<template>
  <div>
    <h2 class="page-title">部门管理</h2>
    <div class="app-card">
      <div class="toolbar">
        <span class="muted">共 {{ departments.length }} 个部门</span>
        <div class="spacer" />
        <el-button type="primary" :icon="Plus" @click="openCreate">新建部门</el-button>
      </div>

      <div class="table-wrap">
        <el-table v-loading="loading" :data="departments">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="name" label="部门名称" min-width="160" />
          <el-table-column prop="code" label="编码" min-width="130" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="170">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <el-dialog v-model="createVisible" title="新建部门" width="440px">
      <el-form ref="createRef" :model="createForm" :rules="rules" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="createForm.name" maxlength="100" />
        </el-form-item>
        <el-form-item label="编码" prop="code">
          <el-input v-model="createForm.code" maxlength="50" placeholder="如 OUTPATIENT" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="saving" @click="doCreate">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editVisible" :title="`编辑部门：${editForm.name}`" width="440px">
      <el-form ref="editRef" :model="editForm" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="editForm.name" maxlength="100" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="editForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="saving" @click="doEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

import * as adminApi from '@/api/admin'
import type { Department } from '@/types'
import { formatDateTime } from '@/utils/format'

const departments = ref<Department[]>([])
const loading = ref(false)
const saving = ref(false)

const createVisible = ref(false)
const createRef = ref<FormInstance>()
const createForm = reactive({ name: '', code: '' })
const rules: FormRules = {
  name: [{ required: true, message: '请输入部门名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入部门编码', trigger: 'blur' }],
}

const editVisible = ref(false)
const editRef = ref<FormInstance>()
const editForm = reactive({ id: 0, name: '', is_active: true })

async function load() {
  loading.value = true
  try {
    const { data } = await adminApi.listDepartments()
    departments.value = data
  } catch {
    /* ignore */
  } finally {
    loading.value = false
  }
}

function openCreate() {
  createForm.name = ''
  createForm.code = ''
  createVisible.value = true
}

async function doCreate() {
  if (!createRef.value) return
  try {
    await createRef.value.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    await adminApi.createDepartment({ name: createForm.name.trim(), code: createForm.code.trim() })
    ElMessage.success('部门已创建')
    createVisible.value = false
    await load()
  } catch {
    /* ignore */
  } finally {
    saving.value = false
  }
}

function openEdit(row: Department) {
  Object.assign(editForm, { id: row.id, name: row.name, is_active: row.is_active })
  editVisible.value = true
}

async function doEdit() {
  saving.value = true
  try {
    await adminApi.updateDepartment(editForm.id, { name: editForm.name.trim(), is_active: editForm.is_active })
    ElMessage.success('部门已更新')
    editVisible.value = false
    await load()
  } catch {
    /* ignore */
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>
