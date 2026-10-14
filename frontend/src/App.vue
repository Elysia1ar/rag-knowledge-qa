<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()

const isLoginPage = computed(() => route.path === '/login')

const HISTORY_KEY = '__history__'

interface MenuItem {
  key: string
  icon: string
  title: string
  action?: () => void
}

const menus = computed<MenuItem[]>(() => {
  const items: MenuItem[] = [
    { key: '/chat', icon: 'ChatDotRound', title: '智能问答' },
    {
      key: HISTORY_KEY,
      icon: 'Clock',
      title: '历史会话',
      action: () => ui.openHistory(),
    },
  ]
  if (auth.isAdmin) {
    items.push(
      { key: '/documents', icon: 'Document', title: '文档管理' },
      { key: '/status', icon: 'Monitor', title: '系统状态' },
    )
  }
  return items
})

const highlighted = computed(() => route.path)

function onMenuSelect(key: string) {
  const item = menus.value.find((m) => m.key === key)
  if (item?.action) {
    item.action()
  } else {
    router.push(key)
  }
}

async function onLogout() {
  try {
    await ElMessageBox.confirm('确定退出登录吗？', '提示', {
      type: 'warning',
      confirmButtonText: '退出',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  auth.logout()
  router.replace('/login')
}
</script>

<template>
  <router-view v-if="isLoginPage" />

  <el-container v-else class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <span class="logo-mark">R</span>
        <span class="logo-text">RAG 知识库</span>
      </div>

      <el-menu
        :default-active="highlighted"
        class="menu"
        @select="onMenuSelect"
      >
        <el-menu-item v-for="m in menus" :key="m.key" :index="m.key">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.title }}</span>
        </el-menu-item>
      </el-menu>

      <div class="user-box">
        <div class="user-info">
          <el-icon><UserFilled /></el-icon>
          <div>
            <div class="user-name">{{ auth.username }}</div>
            <div class="user-role">
              {{ auth.isAdmin ? '管理员' : '普通用户' }}
            </div>
          </div>
        </div>
        <el-button link size="small" @click="onLogout">退出</el-button>
      </div>
    </el-aside>

    <el-main class="main">
      <router-view v-slot="{ Component }">
        <keep-alive :include="['ChatView']">
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </el-main>
  </el-container>
</template>

<style scoped>
.layout { height: 100vh; }

.aside {
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px;
  border-bottom: 1px solid #e4e7ed;
}

.logo-mark {
  width: 30px; height: 30px;
  border-radius: 6px;
  background: linear-gradient(135deg, #409eff, #6366f1);
  color: #fff;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-text { font-weight: 600; font-size: 15px; }

.menu { border-right: none; flex: 1; }

.user-box {
  padding: 12px 16px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
}

.user-name { font-size: 13px; font-weight: 500; color: #303133; }
.user-role { font-size: 11px; color: #909399; }

.main { padding: 0; background: #f5f7fa; overflow: hidden; }
</style>