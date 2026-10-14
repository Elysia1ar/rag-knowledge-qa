<script setup lang="ts">
import { computed, ref } from 'vue'
import type { AgentStep } from '@/types'

const props = defineProps<{
  steps: AgentStep[]
  streaming?: boolean
}>()

const collapsed = ref(false)

const hasSteps = computed(() => props.steps.length > 0)

// 工具名 → 中文描述
const toolLabel: Record<string, string> = {
  search_knowledge: '检索知识库',
  get_current_time: '获取当前时间',
  list_documents: '列出文档',
}

function labelOf(name?: string): string {
  return name ? (toolLabel[name] || name) : '工具'
}

function formatArgs(args?: Record<string, any>): string {
  if (!args) return ''
  return Object.entries(args)
    .map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`)
    .join(', ')
}
</script>

<template>
  <div v-if="hasSteps" class="steps">
    <div class="steps-head" @click="collapsed = !collapsed">
      <el-icon><Loading v-if="streaming" class="spin" /><MagicStick v-else /></el-icon>
      <span>
        思考过程
        <span class="count">({{ steps.length }} 步)</span>
      </span>
      <el-icon class="arrow" :class="{ up: !collapsed }">
        <ArrowDown />
      </el-icon>
    </div>

    <transition name="el-fade-in">
      <div v-show="!collapsed" class="steps-body">
        <div
          v-for="(step, i) in steps"
          :key="i"
          class="step"
          :class="step.type"
        >
          <!-- Action -->
          <template v-if="step.type === 'action'">
            <div class="step-icon action-icon">
              <el-icon><Search /></el-icon>
            </div>
            <div class="step-content">
              <div class="step-title">
                调用工具 · <b>{{ labelOf(step.name) }}</b>
              </div>
              <div v-if="step.args && Object.keys(step.args).length" class="step-args">
                {{ formatArgs(step.args) }}
              </div>
            </div>
          </template>

          <!-- Observation -->
          <template v-else>
            <div class="step-icon observation-icon">
              <el-icon><Document /></el-icon>
            </div>
            <div class="step-content">
              <div class="step-title">工具返回</div>
              <div class="step-preview">{{ step.content }}</div>
            </div>
          </template>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.steps {
  margin-top: 12px;
  background: #f5f3ff;
  border: 1px solid #e0d9ff;
  border-radius: 8px;
  overflow: hidden;
}

.steps-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  font-size: 13px;
  color: #6b21a8;
  cursor: pointer;
  user-select: none;
  font-weight: 500;
}
.steps-head:hover { background: #ede9fe; }

.count { color: #a78bfa; font-weight: 400; margin-left: 4px; }

.arrow { margin-left: auto; transition: transform .2s; }
.arrow.up { transform: rotate(180deg); }

.spin { animation: spin 1.2s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.steps-body {
  border-top: 1px solid #e0d9ff;
  padding: 8px 12px;
  background: #faf8ff;
}

.step {
  display: flex;
  gap: 10px;
  padding: 8px 0;
}
.step + .step { border-top: 1px dashed #e0d9ff; }

.step-icon {
  width: 24px; height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #fff;
  font-size: 13px;
}
.action-icon { background: #8b5cf6; }
.observation-icon { background: #10b981; }

.step-content { flex: 1; min-width: 0; }

.step-title {
  font-size: 12.5px;
  color: #4c1d95;
  margin-bottom: 3px;
}
.step-title b { color: #6b21a8; }

.step-args {
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 11.5px;
  color: #7c3aed;
  background: #ede9fe;
  padding: 4px 8px;
  border-radius: 4px;
  word-break: break-all;
}

.step-preview {
  font-size: 12px;
  color: #606266;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 120px;
  overflow: hidden;
  mask-image: linear-gradient(180deg, #000 70%, transparent);
  -webkit-mask-image: linear-gradient(180deg, #000 70%, transparent);
}
</style>