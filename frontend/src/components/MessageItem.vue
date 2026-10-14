<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import type { Message } from '@/types'
import SourceCard from './SourceCard.vue'
import AgentSteps from './AgentSteps.vue'          // ← 新增
import PlanSteps from './PlanSteps.vue'

const props = defineProps<{ message: Message }>()

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const html = computed(() => md.render(props.message.content || ''))
const isUser = computed(() => props.message.role === 'user')
</script>

<template>
  <div class="msg" :class="{ 'is-user': isUser }">
    <div class="avatar" :class="isUser ? 'user' : 'ai'">
      <el-icon v-if="isUser"><User /></el-icon>
      <el-icon v-else><MagicStick /></el-icon>
    </div>

    <div class="bubble-wrap">
      <div class="bubble">
        <div v-if="isUser" class="text-plain">{{ message.content }}</div>
        <div v-else class="markdown-body" v-html="html" />
        <span v-if="message.status === 'streaming'" class="cursor">▋</span>
      </div>

      <!-- Plan-and-Solve 的执行计划 -->
      <PlanSteps
        v-if="!isUser && message.plan"
        :plan="message.plan"
        :executions="message.executions || []"
        :streaming="message.status === 'streaming'"
      />

      <!-- Agent 思考链：放在气泡下方、来源上方 -->
      <AgentSteps
        v-if="!isUser && message.steps && message.steps.length"
        :steps="message.steps"
        :streaming="message.status === 'streaming'"
      />

      <!-- 记忆使用提示 -->
      <div
        v-if="!isUser && message.memoryCount && message.memoryCount > 0"
        class="memory-hint"
      >
        <el-icon><Star /></el-icon>
        <span>已参考 {{ message.memoryCount }} 条历史记忆</span>
      </div>

      <SourceCard
        v-if="!isUser && message.sources && message.sources.length"
        :sources="message.sources"
      />
    </div>
  </div>
</template>

<style scoped>
.msg {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  align-items: flex-start;
}
.msg.is-user { flex-direction: row-reverse; }

.avatar {
  width: 34px; height: 34px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  color: #fff;
  font-size: 18px;
}
.avatar.user { background: #409eff; }
.avatar.ai   { background: linear-gradient(135deg, #6366f1, #8b5cf6); }

.bubble-wrap { max-width: 78%; }

.bubble {
  padding: 12px 16px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
  position: relative;
}
.is-user .bubble {
  background: #409eff;
  color: #fff;
  border-top-right-radius: 2px;
}
.is-user .bubble-wrap { display: flex; flex-direction: column; align-items: flex-end; }

:not(.is-user) .bubble {
  background: #fff;
  color: #1f2d3d;
  border: 1px solid #e4e7ed;
  border-top-left-radius: 2px;
}

.text-plain { white-space: pre-wrap; }

.markdown-body :deep(p) { margin: 0 0 8px; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(code) {
  background: #f0f2f5;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 13px;
  font-family: ui-monospace, Menlo, Consolas, monospace;
}
.markdown-body :deep(pre) {
  background: #f8fafc;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
}
.markdown-body :deep(pre code) { background: transparent; padding: 0; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { padding-left: 22px; margin: 6px 0; }
.markdown-body :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 13px;
}
.markdown-body :deep(th), .markdown-body :deep(td) {
  border: 1px solid #e4e7ed;
  padding: 5px 10px;
}
.markdown-body :deep(th) { background: #f8fafc; }

.cursor {
  color: #409eff;
  animation: blink 1s infinite;
  margin-left: 2px;
}

.memory-hint {
  margin-top: 10px;
  padding: 6px 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #8b5cf6;
  background: #f5f3ff;
  border: 1px solid #e0d9ff;
  border-radius: 6px;
}

@keyframes blink { 50% { opacity: 0; } }
</style>