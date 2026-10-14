<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { storeToRefs } from 'pinia'
import { useChatStore } from '@/stores/chat'
import type { SessionItem } from '@/types'

const emit = defineEmits<{
  (e: 'switch', id: string): void
}>()

const chat = useChatStore()
const { sessionList, sessionId, isLoading } = storeToRefs(chat)

const keyword = ref('')
const renamingId = ref<string | null>(null)
const renameInput = ref('')

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return sessionList.value
  return sessionList.value.filter((s) =>
    s.title.toLowerCase().includes(kw),
  )
})

function formatTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()

  const pad = (n: number) => String(n).padStart(2, '0')
  if (sameDay) return `${pad(d.getHours())}:${pad(d.getMinutes())}`

  const diff = now.getTime() - d.getTime()
  const dayDiff = Math.floor(diff / 86400000)
  if (dayDiff === 1) return '昨天'
  if (dayDiff < 7) return `${dayDiff} 天前`

  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function onSwitch(s: SessionItem) {
  if (s.id === sessionId.value) return
  emit('switch', s.id)
}

function onNew() {
  chat.newSession()
}

function startRename(s: SessionItem) {
  renamingId.value = s.id
  renameInput.value = s.title
}

async function confirmRename(s: SessionItem) {
  const title = renameInput.value.trim()
  if (!title || title === s.title) {
    renamingId.value = null
    return
  }
  try {
    await chat.renameSession(s.id, title)
    ElMessage.success('已重命名')
  } finally {
    renamingId.value = null
  }
}

async function onDelete(s: SessionItem) {
  try {
    await ElMessageBox.confirm(
      `确定要删除「${s.title}」吗？此操作不可恢复。`,
      '删除会话',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await chat.removeSession(s.id)
    ElMessage.success('已删除')
  } catch {
    // 拦截器已提示
  }
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-head">
      <el-input
        v-model="keyword"
        placeholder="搜索会话"
        size="small"
        clearable
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button
        type="primary"
        size="small"
        :icon="'Plus'"
        @click="onNew"
        :disabled="isLoading"
      />
    </div>

    <el-scrollbar class="sidebar-scroll">
      <div v-if="filtered.length === 0" class="empty-tip">
        暂无历史会话
      </div>

      <div
        v-for="s in filtered"
        :key="s.id"
        class="session-item"
        :class="{ active: s.id === sessionId }"
        @click="onSwitch(s)"
      >
        <div class="item-main">
          <el-icon class="item-icon"><ChatDotSquare /></el-icon>

          <div class="item-info">
            <template v-if="renamingId === s.id">
              <el-input
                v-model="renameInput"
                size="small"
                @click.stop
                @keyup.enter="confirmRename(s)"
                @keyup.esc="renamingId = null"
                @blur="confirmRename(s)"
                v-focus
              />
            </template>
            <template v-else>
              <div class="item-title" :title="s.title">{{ s.title }}</div>
              <div class="item-meta">
                <span>{{ formatTime(s.updated_at) }}</span>
                <span class="dot">·</span>
                <span>{{ s.message_count }} 条</span>
                <el-tooltip
                  v-if="s.has_summary"
                  content="较早期的对话已压缩为摘要，节省 token"
                  placement="top"
                >
                  <span class="summary-badge">📝 已摘要</span>
                </el-tooltip>
              </div>
            </template>
          </div>
        </div>

        <div v-if="renamingId !== s.id" class="item-actions" @click.stop>
          <el-icon
            class="action-icon"
            title="重命名"
            @click="startRename(s)"
          ><Edit /></el-icon>
          <el-icon
            class="action-icon danger"
            title="删除"
            @click="onDelete(s)"
          ><Delete /></el-icon>
        </div>
      </div>
    </el-scrollbar>
  </aside>
</template>

<script lang="ts">
// 输入框自动聚焦（只在组件内用）
export default {
  directives: {
    focus: {
      mounted(el: HTMLElement) {
        const input = el.querySelector('input')
        if (input) {
          input.focus()
          input.select()
        }
      },
    },
  },
}
</script>

<style scoped>
.sidebar {
  width: 100%;
  height: 100%;
  background: #fff;
  display: flex;
  flex-direction: column;
}

.sidebar-head {
  padding: 12px;
  display: flex;
  gap: 8px;
  border-bottom: 1px solid #e4e7ed;
}

.sidebar-scroll {
  flex: 1;
  padding: 8px;
  display: flex;
  flex-direction: column;
}

.empty-tip {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #c0c4cc;
}

.session-item {
  display: flex;
  align-items: center;
  padding: 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background .15s;
  margin-bottom: 2px;
  position: relative;
}
.session-item:hover { background: #eef2f7; }
.session-item.active {
  background: #e6f0ff;
}
.session-item.active .item-title { color: #409eff; font-weight: 500; }

.item-main {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.item-icon {
  color: #909399;
  margin-top: 2px;
  flex-shrink: 0;
  font-size: 14px;
}
.session-item.active .item-icon { color: #409eff; }

.item-info {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 3px;
}

.item-meta {
  font-size: 11px;
  color: #a8abb2;
  display: flex;
  gap: 4px;
}
.dot { color: #d0d3d9; }

.item-actions {
  display: none;
  gap: 4px;
  margin-left: 4px;
  flex-shrink: 0;
}
.session-item:hover .item-actions { display: flex; }

.action-icon {
  font-size: 14px;
  color: #909399;
  padding: 2px;
  border-radius: 4px;
  transition: all .15s;
}
.action-icon:hover { background: #fff; color: #409eff; }
.action-icon.danger:hover { color: #f56c6c; }

.summary-badge {
  color: #8b5cf6;
  background: #f5f3ff;
  padding: 0 4px;
  border-radius: 3px;
  font-size: 10px;
  cursor: help;
}
</style>