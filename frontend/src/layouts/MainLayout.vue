<template>
  <el-container class="layout">
    <!-- 桌面端侧边栏 -->
    <el-aside v-if="!isMobile" width="220px" class="layout-aside">
      <div class="brand">
        <div class="brand-logo">医</div>
        <div class="brand-text">
          <div class="brand-name">医院匿名留言板</div>
          <div class="brand-sub">{{ roleTextLabel }}</div>
        </div>
      </div>
      <el-menu :default-active="activeMenu" class="layout-menu" @select="onMenuSelect">
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container class="layout-body">
      <el-header class="layout-header">
        <div class="header-left">
          <el-button v-if="isMobile" text class="menu-toggle" @click="drawerOpen = true">
            <el-icon size="20"><Expand /></el-icon>
          </el-button>
          <span class="header-title">{{ pageTitle }}</span>
        </div>
        <div class="header-right">
          <el-tag size="small" effect="plain" class="role-tag">{{ roleTextLabel }}</el-tag>
          <el-dropdown trigger="click" @command="onCommand">
            <span class="user-chip">
              <span class="user-avatar">{{ avatarChar }}</span>
              <span class="user-name">{{ auth.displayName }}</span>
              <el-icon class="user-caret"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="password">
                  <el-icon><Key /></el-icon>修改密码
                </el-dropdown-item>
                <el-dropdown-item command="logout" divided>
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>

    <!-- 移动端抽屉导航 -->
    <el-drawer v-model="drawerOpen" direction="ltr" size="240px" :with-header="false" class="mobile-drawer">
      <div class="brand drawer-brand">
        <div class="brand-logo">医</div>
        <div class="brand-text">
          <div class="brand-name">医院匿名留言板</div>
          <div class="brand-sub">{{ roleTextLabel }}</div>
        </div>
      </div>
      <el-menu :default-active="activeMenu" @select="onMenuSelect">
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-drawer>

    <!-- 自愿修改密码弹窗 -->
    <ChangePasswordDialog v-model="pwdDialogVisible" />
  </el-container>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import ChangePasswordDialog from '@/components/ChangePasswordDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { roleText } from '@/utils/status'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

interface MenuItem {
  path: string
  title: string
  icon: string
}

const menus = computed<MenuItem[]>(() => {
  switch (auth.role) {
    case 'principal':
      return [{ path: '/principal', title: '留言列表', icon: 'Document' }]
    case 'secretary':
      return [
        { path: '/secretary', title: '留言列表', icon: 'Document' },
        { path: '/secretary/tasks', title: '任务列表', icon: 'Tickets' },
      ]
    case 'department':
      return [{ path: '/department', title: '任务列表', icon: 'Tickets' }]
    case 'admin':
      return [
        { path: '/admin/users', title: '用户管理', icon: 'User' },
        { path: '/admin/departments', title: '部门管理', icon: 'OfficeBuilding' },
        { path: '/admin/configs', title: '系统配置', icon: 'Setting' },
        { path: '/admin/logs', title: '日志查询', icon: 'Document' },
        { path: '/admin/captcha-reset', title: '验证码重置', icon: 'Key' },
        { path: '/admin/blacklist', title: 'IP 黑名单', icon: 'Lock' },
      ]
    default:
      return []
  }
})

const activeMenu = computed(() => {
  const path = route.path
  const matched = [...menus.value]
    .sort((a, b) => b.path.length - a.path.length)
    .find((m) => path === m.path || path.startsWith(`${m.path}/`))
  return matched?.path ?? ''
})

const pageTitle = computed(() => (route.meta.title as string) || '')
const roleTextLabel = computed(() => roleText(auth.role))
const avatarChar = computed(() => (auth.displayName || '医').slice(0, 1))

const isMobile = ref(false)
const drawerOpen = ref(false)
const pwdDialogVisible = ref(false)
let mql: MediaQueryList | null = null

function onResize(e: MediaQueryListEvent) {
  isMobile.value = e.matches
}

onMounted(() => {
  mql = window.matchMedia('(max-width: 768px)')
  isMobile.value = mql.matches
  mql.addEventListener('change', onResize)
})

onBeforeUnmount(() => {
  mql?.removeEventListener('change', onResize)
})

function onMenuSelect(path: string) {
  drawerOpen.value = false
  if (path !== route.path) router.push(path)
}

function onCommand(cmd: string) {
  if (cmd === 'password') {
    pwdDialogVisible.value = true
  } else if (cmd === 'logout') {
    void doLogout()
  }
}

async function doLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '退出登录', {
      confirmButtonText: '退出',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  auth.logout()
  ElMessage.success('已退出登录')
  router.push({ name: 'login' })
}
</script>

<style scoped>
.layout {
  min-height: 100vh;
}

.layout-aside {
  background: #fff;
  border-right: 1px solid #eef2f2;
  display: flex;
  flex-direction: column;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
}

.brand-logo {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: #0e7a78;
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.brand-name {
  font-size: 15px;
  font-weight: 600;
  color: #0b615f;
  line-height: 1.3;
}

.brand-sub {
  font-size: 12px;
  color: #9aa7b3;
}

.layout-menu {
  border-right: none;
  flex: 1;
}

.layout-menu :deep(.el-menu-item.is-active) {
  background: #e6f4f3;
  color: #0e7a78;
  border-right: 3px solid #0e7a78;
}

.layout-body {
  min-width: 0;
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #eef2f2;
  height: 56px;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.menu-toggle {
  margin-left: -8px;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #2c3e50;
  outline: none;
}

.user-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #0e7a78;
  color: #fff;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-name {
  font-size: 14px;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-caret {
  color: #9aa7b3;
}

.layout-main {
  padding: 20px;
  background: var(--hmb-bg);
}

.drawer-brand {
  border-bottom: 1px solid #eef2f2;
  margin-bottom: 8px;
}

@media (max-width: 768px) {
  .layout-main {
    padding: 12px;
  }
  .layout-header {
    padding: 0 12px;
  }
  .role-tag {
    display: none;
  }
  .user-name {
    max-width: 90px;
  }
}
</style>
