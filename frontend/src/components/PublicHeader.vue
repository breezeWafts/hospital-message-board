<template>
  <div class="public-shell">
    <header class="public-header">
      <div class="public-brand">
        <div class="brand-logo">医</div>
        <div class="brand-texts">
          <div class="public-title">医院匿名留言板系统</div>
          <div class="public-subtitle">Hospital Anonymous Message Board</div>
        </div>
      </div>
      <nav class="public-nav">
        <router-link to="/" :class="{ active: route.name === 'submit' || route.name === 'submit-success' }">我要留言</router-link>
        <router-link to="/query" :class="{ active: route.name === 'query' || route.name === 'evaluate' }">进度查询</router-link>
        <router-link to="/login">员工登录</router-link>
      </nav>
    </header>

    <main class="public-main">
      <slot />
    </main>

    <footer class="public-footer">
      本平台为匿名留言 · 请妥善保管留言编号与查询验证码 · 如有疑问请联系医院办公室
    </footer>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<style scoped>
.public-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.public-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding: 14px 24px;
  background: #fff;
  box-shadow: 0 1px 8px rgba(11, 97, 95, 0.08);
}

.public-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-logo {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  background: #0e7a78;
  color: #fff;
  font-size: 22px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.public-title {
  font-size: 18px;
  font-weight: 600;
  color: #0b615f;
  line-height: 1.3;
}

.public-subtitle {
  font-size: 12px;
  color: #9aa7b3;
}

.public-nav {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.public-nav a {
  display: inline-block;
  padding: 8px 16px;
  border-radius: 8px;
  color: #2c3e50;
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
}

.public-nav a:hover {
  background: #e6f4f3;
  color: #0e7a78;
}

.public-nav a.active {
  background: #0e7a78;
  color: #fff;
}

.public-main {
  flex: 1;
  width: 100%;
  max-width: 980px;
  margin: 0 auto;
  padding: 24px 16px 40px;
}

.public-footer {
  text-align: center;
  font-size: 12px;
  color: #9aa7b3;
  padding: 16px;
}

@media (max-width: 640px) {
  .public-header {
    padding: 12px 14px;
  }
  .public-title {
    font-size: 16px;
  }
  .public-subtitle {
    display: none;
  }
  .public-nav a {
    padding: 6px 12px;
    font-size: 13px;
  }
}
</style>
