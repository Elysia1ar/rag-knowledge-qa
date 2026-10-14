<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { useChatStore } from '@/stores/chat'
import { useUiStore } from '@/stores/ui'
import MessageItem from '@/components/MessageItem.vue'
import SessionSidebar from '@/components/SessionSidebar.vue'

defineOptions({ name: 'ChatView' })

const chat = useChatStore()
const ui = useUiStore()
const { messages, isLoading, sessionId, mode, sessionLoading, currentSessionTitle } = storeToRefs(chat)

const input = ref('')
const scrollBox = ref<HTMLElement | null>(null)

onMounted(() => {
  chat.loadSessions()
})

async function scrollToBottom() {
  await nextTick()
  if (scrollBox.value) {
    scrollBox.value.scrollTop = scrollBox.value.scrollHeight
  }
}

watch(messages, scrollToBottom, { deep: true })

async function onSubmit() {
  const q = input.value.trim()
  if (!q) return
  if (isLoading.value) {
    ElMessage.warning('上一条还在生成中')
    return
  }
  input.value = ''
  await chat.send(q)
}

function onKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault()
    onSubmit()
  }
}

function onModeChange(newMode: 'rag' | 'agent' | 'plan') {
  if (isLoading.value) return
  chat.setMode(newMode)
}

async function onSwitchSession(id: string) {
  await chat.switchSession(id)
  scrollToBottom()
  ui.closeHistory()          // 切换后自动关闭抽屉
}

function onNewSession() {
  chat.newSession()
  input.value = ''
  ui.closeHistory()
}
</script>

<template>
  <div class="chat-view">
    <header class="chat-head">
      <div class="title-wrap">
        <div class="title">{{ currentSessionTitle || '智能问答' }}</div>
        <div v-if="sessionId" class="title-sub">会话 {{ sessionId.slice(0, 8) }}</div>
      </div>
      <div class="head-right">
        <el-radio-group
          v-model="mode"
          size="small"
          :disabled="isLoading"
          @change="onModeChange"
        >
          <el-radio-button value="rag">
            <el-icon><ChatDotRound /></el-icon>
            普通问答
          </el-radio-button>
          <el-radio-button value="agent">
            <el-icon><MagicStick /></el-icon>
            ReAct
          </el-radio-button>
          <el-radio-button value="plan">
            <el-icon><Notebook /></el-icon>
            Plan-and-Solve
          </el-radio-button>
        </el-radio-group>
        <el-button size="small" @click="onNewSession" :disabled="isLoading">
          新会话
        </el-button>
      </div>
    </header>

    <div ref="scrollBox" class="scroll" v-loading="sessionLoading">
      <div v-if="!sessionLoading && messages.length === 0" class="empty">
        <div class="empty-icon">
          <el-icon>
            <MagicStick v-if="mode !== 'rag'" />
            <ChatDotRound v-else />
          </el-icon>
        </div>
        <div class="empty-title">
          {{
            mode === 'agent' ? 'ReAct 模式已开启'
            : mode === 'plan' ? 'Plan-and-Solve 模式已开启'
            : '你好，我是你的知识库助手'
          }}
        </div>
        <div class="empty-tip">
          {{
            mode === 'agent' ? 'Agent 会自主规划、调用工具、多步推理'
            : mode === 'plan' ? 'Agent 会先制定完整计划，再逐步执行'
            : '试试问我：RAG 的典型管线包括哪些步骤？'
          }}
        </div>
      </div>

      <MessageItem
        v-for="m in messages"
        :key="m.id"
        :message="m"
      />
    </div>

    <footer class="chat-input">
      <el-input
        v-model="input"
        type="textarea"
        :rows="3"
        resize="none"
        placeholder="输入问题，Ctrl + Enter 发送"
        :disabled="isLoading"
        @keydown="onKeydown"
      />
      <div class="actions">
        <el-button
          v-if="isLoading"
          type="warning"
          @click="chat.stop()"
        >停止生成</el-button>
        <el-button
          v-else
          type="primary"
          :disabled="!input.trim()"
          @click="onSubmit"
        >发送</el-button>
      </div>
    </footer>

    <!-- 历史会话抽屉：从右侧滑出 -->
    <el-drawer
      v-model="ui.historyDrawerOpen"
      direction="rtl"
      size="320px"
      :with-header="false"
      :append-to-body="true"
      class="history-drawer"
    >
      <SessionSidebar @switch="onSwitchSession" />
    </el-drawer>
  </div>
</template>

<style scoped>
.chat-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
}

.chat-head {
  height: 56px;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.title { font-size: 15px; font-weight: 600; }

.head-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.head-right :deep(.el-radio-button__inner) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.title-wrap {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.title {
  font-size: 15px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 400px;
}
.title-sub {
  font-size: 11.5px;
  color: #909399;
  font-family: monospace;
}

.scroll {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
}

.empty {
  text-align: center;
  padding-top: 80px;
  color: #909399;
}
.empty-icon {
  font-size: 48px;
  color: #c0c4cc;
  margin-bottom: 12px;
}
.empty-title { font-size: 16px; color: #606266; margin-bottom: 6px; }
.empty-tip { font-size: 13px; }

.chat-input {
  padding: 14px 24px 18px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
  flex-shrink: 0;
}
.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}
</style>

<style>
/* 抽屉全局样式：去掉默认内边距 */
.history-drawer .el-drawer__body {
  padding: 0;
  overflow: hidden;
}
</style>