<template>
  <div>
    <h2 class="page-title">用户管理</h2>
    <div class="app-card">
      <div class="toolbar">
        <el-input v-model="search" placeholder="搜索用户名/姓名/手机号" clearable style="width: 240px" @keyup.enter="onSearch" @clear="onSearch" />
        <el-button type="primary" @click="onSearch">查询</el-button>
        <div class="spacer" />
        <el-button type="primary" :icon="Plus" @click="openCreate">新建用户</el-button>
      </div>

      <div class="table-wrap">
        <el-table v-loading="loading" :data="items">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="username" label="用户名" min-width="130" show-overflow-tooltip />
          <el-table-column prop="display_name" label="姓名" min-width="100" show-overflow-tooltip />
          <el-table-column label="认证方式" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.auth_source === 'oauth2'" type="info" size="small">统一认证</el-tag>
              <el-tag v-else size="small">本地</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="角色" width="110">
            <template #default="{ row }">
              <el-tag v-if="row.role" :type="row.role === 'admin' ? 'danger' : 'primary'" size="small">{{ roleText(row.role) }}</el-tag>
              <el-tag v-else type="warning" size="small">待授权</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="department_name" label="部门" min-width="120" show-overflow-tooltip />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="openEdit(row)">
                {{ !row.role || !row.is_active ? '授权' : '编辑' }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="load"
          @size-change="onSizeChange"
        />
      </div>
    </div>

    <!-- 新建用户 -->
    <el-dialog v-model="createVisible" title="新建用户" width="520px">
      <el-form ref="createRef" :model="createForm" :rules="createRules" label-width="110px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="createForm.username" maxlength="64" />
        </el-form-item>
        <el-form-item label="初始密码" prop="password">
          <el-input v-model="createForm.password" type="password" show-password placeholder="至少 8 位，含字母和数字" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="createForm.display_name" maxlength="100" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="createForm.phone" maxlength="30" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="createForm.email" maxlength="200" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="createForm.role" placeholder="选择角色" style="width: 100%">
            <el-option v-for="r in ROLE_OPTIONS" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门" prop="department_id">
          <el-select v-model="createForm.department_id" placeholder="部门负责人需指定部门" clearable style="width: 100%">
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="createForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="saving" @click="doCreate">保存</el-button>
      </template>
    </el-dialog>

    <!-- 编辑 / 统一认证授权 -->
    <el-dialog v-model="editVisible" :title="editForm.id ? `编辑用户：${editForm.username}` : '编辑用户'" width="520px">
      <el-alert
        v-if="editTarget && editTarget.auth_source === 'oauth2' && (!editTarget.role || !editTarget.is_active)"
        type="warning"
        :closable="false"
        show-icon
        title="统一认证用户待授权：请分配角色与部门并启用账号。"
        style="margin-bottom: 12px"
      />
      <el-form ref="editRef" :model="editForm" :rules="editRules" label-width="110px">
        <el-form-item label="姓名">
          <el-input v-model="editForm.display_name" maxlength="100" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="editForm.phone" maxlength="30" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" maxlength="200" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="editForm.role" placeholder="选择角色" style="width: 100%">
            <el-option v-for="r in ROLE_OPTIONS" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门" prop="department_id">
          <el-select v-model="editForm.department_id" placeholder="部门负责人需指定部门" clearable style="width: 100%">
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="editForm.is_active" />
        </el-form-item>
        <el-form-item label="重置密码" prop="password">
          <el-input v-model="editForm.password" type="password" show-password placeholder="留空则不修改；设置后用户下次登录须改密" />
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
import type { Department, User } from '@/types'
import { roleText } from '@/utils/status'

const ROLE_OPTIONS = [
  { value: 'admin', label: '系统管理员' },
  { value: 'principal', label: '院长' },
  { value: 'secretary', label: '秘书' },
  { value: 'department', label: '部门负责人' },
]

const search = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const items = ref<User[]>([])
const loading = ref(false)
const departments = ref<Department[]>([])
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await adminApi.listUsers({ search: search.value || undefined, page: page.value, page_size: pageSize.value })
    items.value = data.items
    total.value = data.total
  } catch {
    /* ignore */
  } finally {
    loading.value = false
  }
}

async function loadDepartments() {
  try {
    const { data } = await adminApi.listDepartments()
    departments.value = data
  } catch {
    departments.value = []
  }
}

function onSearch() {
  page.value = 1
  void load()
}

function onSizeChange() {
  page.value = 1
  void load()
}

// ---------- 新建 ----------
const createVisible = ref(false)
const createRef = ref<FormInstance>()
const createForm = reactive({
  username: '',
  password: '',
  display_name: '',
  phone: '',
  email: '',
  role: '' as string,
  department_id: null as number | null,
  is_active: true,
})

const createRules = computedRules()

function computedRules(): FormRules {
  return {
    username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
    password: [
      {
        validator: (_r: unknown, v: string, cb: (e?: Error) => void) => {
          if (!v) cb()
          else if (v.length >= 8 && /[a-zA-Z]/.test(v) && /\d/.test(v)) cb()
          else cb(new Error('密码至少 8 位，且必须同时包含字母和数字'))
        },
        trigger: 'blur',
      },
    ],
    role: [{ required: true, message: '请选择角色', trigger: 'change' }],
    department_id: [
      {
        validator: (_r: unknown, v: number | null, cb: (e?: Error) => void) => {
          if (createForm.role === 'department' && !v) cb(new Error('部门负责人必须指定部门'))
          else cb()
        },
        trigger: 'change',
      },
    ],
  }
}

function openCreate() {
  Object.assign(createForm, {
    username: '',
    password: '',
    display_name: '',
    phone: '',
    email: '',
    role: '',
    department_id: null,
    is_active: true,
  })
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
    await adminApi.createUser({
      username: createForm.username.trim(),
      password: createForm.password || undefined,
      display_name: createForm.display_name.trim() || undefined,
      phone: createForm.phone.trim() || undefined,
      email: createForm.email.trim() || undefined,
      role: createForm.role || null,
      department_id: createForm.department_id,
      is_active: createForm.is_active,
    })
    ElMessage.success('用户已创建')
    createVisible.value = false
    await load()
  } catch {
    /* ignore */
  } finally {
    saving.value = false
  }
}

// ---------- 编辑 / 授权 ----------
const editVisible = ref(false)
const editRef = ref<FormInstance>()
const editTarget = ref<User | null>(null)
const editForm = reactive({
  id: 0,
  username: '',
  display_name: '',
  phone: '',
  email: '',
  role: '' as string,
  department_id: null as number | null,
  is_active: true,
  password: '',
})

const editRules: FormRules = {
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  department_id: [
    {
      validator: (_r: unknown, v: number | null, cb: (e?: Error) => void) => {
        if (editForm.role === 'department' && !v) cb(new Error('部门负责人必须指定部门'))
        else cb()
      },
      trigger: 'change',
    },
  ],
  password: [
    {
      validator: (_r: unknown, v: string, cb: (e?: Error) => void) => {
        if (!v) cb()
        else if (v.length >= 8 && /[a-zA-Z]/.test(v) && /\d/.test(v)) cb()
        else cb(new Error('密码至少 8 位，且必须同时包含字母和数字'))
      },
      trigger: 'blur',
    },
  ],
}

function openEdit(row: User) {
  editTarget.value = row
  Object.assign(editForm, {
    id: row.id,
    username: row.username,
    display_name: row.display_name || '',
    phone: row.phone || '',
    email: row.email || '',
    role: row.role || '',
    department_id: row.department_id ?? null,
    is_active: !!row.is_active,
    password: '',
  })
  editVisible.value = true
}

async function doEdit() {
  if (!editRef.value) return
  try {
    await editRef.value.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    await adminApi.updateUser(editForm.id, {
      display_name: editForm.display_name.trim() || undefined,
      phone: editForm.phone.trim() || undefined,
      email: editForm.email.trim() || undefined,
      role: editForm.role || null,
      department_id: editForm.department_id,
      is_active: editForm.is_active,
      password: editForm.password || undefined,
    })
    ElMessage.success('用户已更新')
    editVisible.value = false
    await load()
  } catch {
    /* ignore */
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  void load()
  void loadDepartments()
})
</script>
